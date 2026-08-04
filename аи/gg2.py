import cv2
import numpy as np
from datetime import datetime, timedelta
import os
import uuid
import asyncio
import websockets
import json
import base64
import threading
import logging
import signal
import re
import time
from functools import wraps
from ultralytics import YOLO
from werkzeug.utils import secure_filename
from pathlib import Path
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any

import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image
from flask import Flask, Response, request, jsonify

try:
    import winsound
except ImportError:
    winsound = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("vision.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("SmartVision")

CONFIG = {
    "camera_id": "01",
    "ws_url": "ws://127.0.0.1:8005/ws",
    "reconnect_delay": 5,
    "ping_interval": 30,
    "stream_port": 5000,
    "tolerance": 0.85,
    "frame_thickness": 2,
    "font_thickness": 1,
    "analysis_window_seconds": 3,
    "min_detections_for_flicker": 1,
    "flicker_threshold": 0.5,
    "emotion_confidence_threshold": 0.3,
    "weapon_confidence_threshold": 0.7,
    "pose_confidence_threshold": 0.5,
    "max_upload_mb": 16,
    "allowed_extensions": {"png", "jpg", "jpeg"},
    "paths": {
        "known_faces": os.environ.get("KNOWN_FACES_DIR", "known_faces"),
        "uploads": os.environ.get("UPLOAD_FOLDER", "uploads"),
        "reflector_model": os.environ.get(
            "REFLECTOR_MODEL", "yolo_reflector_model/weights/best.pt"
        ),
        "emotion_model": os.environ.get("EMOTION_MODEL", "faceemotion.pt"),
        "weapon_model": os.environ.get("WEAPON_MODEL", "gun_detection/gun.pt"),
        "pose_model": os.environ.get("POSE_MODEL", "yolo26n-pose.pt"),
    },

    "skip_intervals": {
        "face": 1,
        "emotion": 1,
        "weapon": 2,
        "reflector": 4,
        "pose": 1,
    },
}

EMOTION_MAPPING = {
    "Contempt": "Neutral",
    "Disgust": "Negative",
    "Fear": "Negative",
    "Angry": "Aggression",
    "Happy": "Happy",
    "Sad": "Sad",
    "Surprise": "Surprise",
    "Neutral": "Neutral",
}

CAMERA_ID = CONFIG["camera_id"]
STREAM_PORT = CONFIG["stream_port"]

def validate_name(name: str) -> Tuple[bool, str]:
    if not name or len(name) > 50:
        return False, "Имя должно быть от 1 до 50 символов"
    if not re.match(r"^[a-zA-Zа-яА-ЯёЁ\s\-]+$", name):
        return False, "Имя содержит недопустимые символы"
    return True, ""


def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in CONFIG["allowed_extensions"]
    )

class WeaponAlert:
    def __init__(self):
        self._lock = threading.Lock()
        self._last_seen: Optional[datetime] = None

    def trigger(self):
        with self._lock:
            self._last_seen = datetime.now()

    def is_active(self, timeout: float = 2.0) -> bool:
        with self._lock:
            if self._last_seen is None:
                return False
            return (datetime.now() - self._last_seen).total_seconds() < timeout


weapon_alert = WeaponAlert()

class FrameSkipper:
    def __init__(self, intervals: Dict[str, int]):
        self.counters: Dict[str, int] = defaultdict(int)
        self.intervals = intervals

    def should_process(self, task: str) -> bool:
        self.counters[task] += 1
        if self.counters[task] >= self.intervals.get(task, 1):
            self.counters[task] = 0
            return True
        return False

class CameraCapture:
    def __init__(self, cam_id: int, max_failures: int = 30):
        self.cam_id = cam_id
        self.cap = cv2.VideoCapture(cam_id)
        self.fail_count = 0
        self.max_failures = max_failures

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        ret, frame = self.cap.read()
        if not ret:
            self.fail_count += 1
            if self.fail_count >= self.max_failures:
                self._reconnect()
            return False, None
        self.fail_count = 0
        return True, frame

    def _reconnect(self):
        logger.warning(f"🔄 Переподключение камеры {self.cam_id}...")
        self.cap.release()
        time.sleep(1)
        self.cap = cv2.VideoCapture(self.cam_id)
        self.fail_count = 0
        if self.cap.isOpened():
            logger.info(f"✓ Камера {self.cam_id} переподключена")
        else:
            logger.error(f"✗ Камера {self.cam_id} не доступна после переподключения")

    def is_opened(self) -> bool:
        return self.cap.isOpened()

    def release(self):
        self.cap.release()

class CameraFrameManager:
    def __init__(self):
        self.frames: Dict[int, Optional[np.ndarray]] = {}
        self.locks: Dict[int, threading.Lock] = {}
        self.master_lock = threading.Lock()
        self.active_cameras: List[int] = []

    def register_camera(self, cam_id: int):
        with self.master_lock:
            if cam_id not in self.locks:
                self.locks[cam_id] = threading.Lock()
                self.frames[cam_id] = None
                if cam_id not in self.active_cameras:
                    self.active_cameras.append(cam_id)
                logger.info(f"✓ Камера {cam_id} зарегистрирована")

    def update_frame(self, cam_id: int, frame: Optional[np.ndarray]):
        if cam_id not in self.locks:
            self.register_camera(cam_id)
        with self.locks[cam_id]:
            self.frames[cam_id] = frame.copy() if frame is not None else None

    def get_frame(self, cam_id: int) -> Optional[np.ndarray]:
        if cam_id not in self.locks:
            return None
        with self.locks[cam_id]:
            f = self.frames.get(cam_id)
            return f.copy() if f is not None else None

    def get_active_cameras(self) -> List[int]:
        with self.master_lock:
            return list(self.active_cameras)

    def remove_camera(self, cam_id: int):
        with self.master_lock:
            if cam_id in self.active_cameras:
                self.active_cameras.remove(cam_id)
            self.frames.pop(cam_id, None)
            self.locks.pop(cam_id, None)


camera_manager = CameraFrameManager()

@dataclass
class PersonDetection:
    timestamp: datetime
    flicker_detected: bool
    emotion: Optional[str]
    confidence: float = 0.0


@dataclass
class PersonTracker:
    person_key: str
    first_name: str
    last_name: str
    detections: deque = field(default_factory=lambda: deque(maxlen=100))
    last_sent: Optional[datetime] = None

    def add_detection(
        self, flicker: bool, emotion: Optional[str], confidence: float = 0.0
    ):
        self.detections.append(
            PersonDetection(
                timestamp=datetime.now(),
                flicker_detected=flicker,
                emotion=emotion,
                confidence=confidence,
            )
        )
        self._cleanup_old()

    def _cleanup_old(self):
        cutoff = datetime.now() - timedelta(
            seconds=CONFIG["analysis_window_seconds"]
        )
        while self.detections and self.detections[0].timestamp < cutoff:
            self.detections.popleft()

    def get_flicker_status(self) -> Tuple[bool, float]:
        self._cleanup_old()
        if len(self.detections) < CONFIG["min_detections_for_flicker"]:
            return False, 0.0
        flicker_count = sum(1 for d in self.detections if d.flicker_detected)
        confidence = flicker_count / len(self.detections) if self.detections else 0.0
        return confidence >= CONFIG["flicker_threshold"], confidence

    def get_dominant_emotion(self) -> Tuple[Optional[str], float]:
        self._cleanup_old()
        valid = [d for d in self.detections if d.emotion]
        if not valid:
            return None, 0.0
        counts: Dict[str, int] = defaultdict(int)
        for d in valid:
            counts[d.emotion] += 1
        dominant = max(counts, key=counts.get)
        confidence = counts[dominant] / len(valid)
        if confidence >= CONFIG["emotion_confidence_threshold"]:
            return dominant, confidence
        return None, confidence

    def should_send_update(self, hours: int = 1) -> bool:
        if self.last_sent is None:
            return True
        return datetime.now() - self.last_sent > timedelta(hours=hours)


class PersonTrackerManager:
    def __init__(self):
        self.trackers: Dict[str, PersonTracker] = {}
        self.lock = threading.Lock()

    def get_or_create(
        self, key: str, first: str, last: str
    ) -> PersonTracker:
        with self.lock:
            if key not in self.trackers:
                self.trackers[key] = PersonTracker(key, first, last)
            return self.trackers[key]

    def cleanup_inactive(self, minutes: int = 5):
        with self.lock:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            to_remove = [
                k
                for k, t in self.trackers.items()
                if not t.detections or t.detections[-1].timestamp < cutoff
            ]
            for k in to_remove:
                del self.trackers[k]


tracker_manager = PersonTrackerManager()
class KnownFaceManager:
    def __init__(self, faces_dir: str, mtcnn_model, resnet_model, dev):
        self.faces_dir = faces_dir
        self.mtcnn = mtcnn_model
        self.resnet = resnet_model
        self.device = dev
        self.known_face_embeddings: List[np.ndarray] = []
        self.known_persons_data: List[Dict[str, str]] = []
        self._embeddings_matrix: Optional[np.ndarray] = None
        self.lock = threading.Lock()
        self.load_all_faces()

    def _rebuild_matrix(self):
        if self.known_face_embeddings:
            self._embeddings_matrix = np.stack(self.known_face_embeddings)
        else:
            self._embeddings_matrix = None

    def _get_embedding(self, image: Image.Image):
        with torch.no_grad():
            boxes, probs = self.mtcnn.detect(image)
            if boxes is None:
                return None, "Лицо не найдено на изображении"
            if len(boxes) > 1:
                return None, "Найдено несколько лиц. Загрузите фото с одним лицом"
            face_tensor = self.mtcnn.extract(image, boxes, save_path=None)
            if face_tensor is None:
                return None, "Не удалось извлечь лицо"
            embedding = self.resnet(face_tensor.to(self.device))
            return embedding.detach().cpu().numpy(), None

    def load_all_faces(self):
        embeddings: List[np.ndarray] = []
        persons: List[Dict[str, str]] = []
        for filename in os.listdir(self.faces_dir):
            if not filename.lower().endswith((".jpg", ".png", ".jpeg")):
                continue
            name_parts = os.path.splitext(filename)[0].split("_", 1)
            if len(name_parts) != 2:
                continue
            try:
                filepath = os.path.join(self.faces_dir, filename)
                image = Image.open(filepath).convert("RGB")
                emb, err = self._get_embedding(image)
                if emb is not None:
                    embeddings.append(emb[0])
                    persons.append(
                        {
                            "first_name": name_parts[0],
                            "last_name": name_parts[1],
                            "filename": filename,
                        }
                    )
                else:
                    logger.warning(f"Пропуск {filename}: {err}")
            except Exception as e:
                logger.error(f"Ошибка загрузки {filename}: {e}")
        with self.lock:
            self.known_face_embeddings = embeddings
            self.known_persons_data = persons
            self._rebuild_matrix()
        logger.info(f"Загружено {len(self.known_face_embeddings)} известных лиц")

    def add_face(self, image_stream, first_name: str, last_name: str) -> dict:
        try:
            image = Image.open(image_stream).convert("RGB")
            emb, err = self._get_embedding(image)
            if emb is None:
                return {"success": False, "error": err}

            filename = secure_filename(f"{first_name}_{last_name}.jpg")
            output_path = os.path.join(self.faces_dir, filename)
            image.save(output_path, "JPEG")

            with self.lock:
                self.known_face_embeddings.append(emb[0])
                self.known_persons_data.append(
                    {
                        "first_name": first_name,
                        "last_name": last_name,
                        "filename": filename,
                    }
                )
                self._rebuild_matrix()
            logger.info(f"Добавлено лицо: {first_name} {last_name}")
            return {"success": True, "filename": filename}
        except Exception as e:
            return {"success": False, "error": f"Ошибка обработки: {e}"}

    def remove_face(self, filename: str) -> bool:
        safe = secure_filename(filename)
        with self.lock:
            idx = next(
                (
                    i
                    for i, p in enumerate(self.known_persons_data)
                    if p["filename"] == safe
                ),
                -1,
            )
            if idx == -1:
                return False
            self.known_face_embeddings.pop(idx)
            info = self.known_persons_data.pop(idx)
            self._rebuild_matrix()
            filepath = os.path.join(self.faces_dir, safe)
            if os.path.exists(filepath):
                os.remove(filepath)
            logger.info(f"Удалено лицо: {info['first_name']} {info['last_name']}")
            return True

    def find_closest(self, embedding: np.ndarray) -> Tuple[int, float]:
        with self.lock:
            if self._embeddings_matrix is None:
                return -1, float("inf")
            dists = np.linalg.norm(
                self._embeddings_matrix - embedding, axis=1
            )
            best_idx = int(np.argmin(dists))
            return best_idx, float(dists[best_idx])

    def get_recognition_data(self):
        with self.lock:
            return list(self.known_persons_data)

    def get_known_faces_list(self):
        with self.lock:
            return list(self.known_persons_data)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = CONFIG["paths"]["uploads"]
app.config["MAX_CONTENT_LENGTH"] = CONFIG["max_upload_mb"] * 1024 * 1024

os.makedirs(CONFIG["paths"]["known_faces"], exist_ok=True)
os.makedirs(CONFIG["paths"]["uploads"], exist_ok=True)

face_manager: Optional[KnownFaceManager] = None
shutdown_event = threading.Event()

def generate_mjpeg(cam_id: int):
    while not shutdown_event.is_set():
        frame = camera_manager.get_frame(cam_id)
        if frame is not None:
            ok, jpeg = cv2.imencode(".jpg", frame)
            if ok:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + jpeg.tobytes()
                    + b"\r\n"
                )
        time.sleep(0.03)


@app.route(f"/{CAMERA_ID}/video_feed")
def video_feed_default():
    cameras = camera_manager.get_active_cameras()
    if cameras:
        return Response(
            generate_mjpeg(cameras[0]),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
    return "No cameras available", 404


@app.route(f"/{CAMERA_ID}/camera/<int:cam_id>/video_feed")
def video_feed_by_id(cam_id: int):
    if cam_id in camera_manager.get_active_cameras():
        return Response(
            generate_mjpeg(cam_id),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
    return f"Camera {cam_id} not found", 404


@app.route(f"/{CAMERA_ID}/cameras")
def list_cameras():
    cameras = camera_manager.get_active_cameras()
    return jsonify(
        {
            "cameras": cameras,
            "count": len(cameras),
            "streams": {
                cid: f"http://127.0.0.1:{STREAM_PORT}/{CAMERA_ID}/camera/{cid}/video_feed"
                for cid in cameras
            },
        }
    )


@app.route(f"/{CAMERA_ID}/grid")
def camera_grid():
    cameras = camera_manager.get_active_cameras()
    items = "".join(
        f'<div class="camera">'
        f'<div class="camera-label">Camera {c}</div>'
        f'<img src="/{CAMERA_ID}/camera/{c}/video_feed" alt="Camera {c}">'
        f"</div>"
        for c in cameras
    )
    return f"""<!DOCTYPE html><html><head><title>Camera Grid</title>
    <style>
        body{{margin:0;padding:10px;background:#1a1a1a}}
        .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:10px}}
        .camera{{position:relative}}
        .camera img{{width:100%;border-radius:10px}}
        .camera-label{{position:absolute;top:10px;left:10px;background:rgba(0,0,0,.7);
                       color:#fff;padding:5px 10px;border-radius:5px}}
    </style></head><body><div class="grid">{items}</div>
    <script>setInterval(()=>location.reload(),30000);</script>
    </body></html>"""


@app.route(f"/{CAMERA_ID}/api/upload_face", methods=["POST"])
def upload_face():
    if (
        "file" not in request.files
        or "first_name" not in request.form
        or "last_name" not in request.form
    ):
        return jsonify({"error": "file, first_name, last_name required"}), 400

    f = request.files["file"]
    if f.filename == "" or not allowed_file(f.filename):
        return jsonify({"error": "Invalid file"}), 400

    first = request.form["first_name"].strip()
    last = request.form["last_name"].strip()

    ok, err = validate_name(first)
    if not ok:
        return jsonify({"error": f"first_name: {err}"}), 400
    ok, err = validate_name(last)
    if not ok:
        return jsonify({"error": f"last_name: {err}"}), 400

    try:
        res = face_manager.add_face(f.stream, first, last)
        return jsonify(res), 200 if res.get("success") else 400
    except Exception as e:
        logger.error(f"upload_face error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route(f"/{CAMERA_ID}/api/known_faces", methods=["GET"])
def get_known_faces():
    try:
        faces = face_manager.get_known_faces_list()
        return jsonify({"faces": faces}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route(f"/{CAMERA_ID}/api/known_faces/<filename>", methods=["DELETE"])
def delete_known_face(filename: str):
    try:
        if face_manager.remove_face(filename):
            return jsonify({"message": "Face deleted"}), 200
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run_flask():
    app.run(
        host="0.0.0.0",
        port=STREAM_PORT,
        threaded=True,
        use_reloader=False,
    )

def siren_worker():
    while not shutdown_event.is_set():
        if weapon_alert.is_active():
            if winsound:
                try:
                    winsound.Beep(1000, 200)
                    winsound.Beep(1500, 200)
                except Exception:
                    pass
            else:
                time.sleep(0.5)
        else:
            time.sleep(0.1)

def detect_emotion(img: np.ndarray, model) -> Tuple[Optional[str], float]:
    try:
        res = model.predict(img, verbose=False)
        if not res:
            return None, 0.0
        r = res[0]
        names = r.names
        if hasattr(r, "probs") and r.probs is not None:
            raw = names.get(int(r.probs.top1))
            mapped = EMOTION_MAPPING.get(raw, raw)
            return mapped, float(r.probs.top1conf)
        if hasattr(r, "boxes") and r.boxes is not None and len(r.boxes):
            best = r.boxes[r.boxes.conf.argmax()]
            raw = names.get(int(best.cls[0]))
            mapped = EMOTION_MAPPING.get(raw, raw)
            return mapped, float(best.conf[0])
        return None, 0.0
    except Exception:
        return None, 0.0

def process_frame(
    frame: np.ndarray,
    cam_id: int,
    face_mgr: KnownFaceManager,
    skipper: FrameSkipper,
    emotion_model=None,
    weapon_model=None,
    reflector_model=None,
    pose_model=None,
):
    orig = frame.copy()
    display = frame.copy()
    detections_to_send: List[Tuple[PersonTracker, dict]] = []

    if weapon_model and skipper.should_process("weapon"):
        try:
            w_res = weapon_model.predict(
                orig,
                verbose=False,
                conf=CONFIG["weapon_confidence_threshold"],
            )
            for r in w_res:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    weapon_alert.trigger()
                    cv2.rectangle(display, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    label = f"WEAPON! {conf:.2f}"
                    (tw, th), _ = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2
                    )
                    cv2.rectangle(
                        display, (x1, y1 - 25), (x1 + tw, y1), (0, 0, 255), -1
                    )
                    cv2.putText(
                        display,
                        label,
                        (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (255, 255, 255),
                        2,
                    )
        except Exception as e:
            logger.error(f"Weapon detection cam {cam_id}: {e}")

    if pose_model and skipper.should_process("pose"):
        try:
            pose_res = pose_model.predict(orig, verbose=False, conf=0.3, imgsz=480)
            
            BODY_SKELETON = [
                (15, 13), (13, 11), (16, 14), (14, 12),
                (11, 12), (5, 11), (6, 12), (5, 6),
                (5, 7), (6, 8), (7, 9), (8, 10)
            ]
            
            for r in pose_res:
                if r.keypoints is not None and len(r.keypoints) > 0:
                    kpts = r.keypoints.data.cpu().numpy()
                    
                    for person_kpts in kpts:
                        valid_points = {}
                        
                        for j, pt in enumerate(person_kpts):
                            if j < 5: continue
                            x, y, conf = pt[0], pt[1], pt[2]
                            
                            if conf > 0.3 and x > 0 and y > 0:
                                point = (int(x), int(y))
                                valid_points[j] = point
                                cv2.circle(display, point, 5, (255, 0, 255), -1)
                        
                        for p1, p2 in BODY_SKELETON:
                            if p1 in valid_points and p2 in valid_points:
                                cv2.line(display, valid_points[p1], valid_points[p2], (255, 255, 0), 2)
                                
        except Exception as e:
            logger.error(f"Pose error cam {cam_id}: {e}")

    cv2.putText(
        display,
        f"CAM {cam_id}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
    )

    if not skipper.should_process("face"):
        return display, []

    img_pil = Image.fromarray(cv2.cvtColor(orig, cv2.COLOR_BGR2RGB))

    with torch.no_grad():
        boxes, probs = face_mgr.mtcnn.detect(img_pil)
        if boxes is None or probs is None:
            return display, []

        valid_boxes = []
        for box, prob in zip(boxes, probs):
            if prob is None or box is None:
                continue
                
            x1, y1, x2, y2 = box
            width = x2 - x1
            height = y2 - y1

            if prob > 0.90 and width >= 40 and height >= 40:
                valid_boxes.append(box)

        if not valid_boxes:
            return display, []

        face_tensors = face_mgr.mtcnn.extract(img_pil, valid_boxes, save_path=None)
        if face_tensors is None:
            return display, []
            
        embeddings = (
            face_mgr.resnet(face_tensors.to(face_mgr.device))
            .detach()
            .cpu()
            .numpy()
        )

    persons_data = face_mgr.get_recognition_data()

    for i, box in enumerate(valid_boxes):
        x1, y1, x2, y2 = map(int, box)
        face_roi = orig[max(0, y1): max(0, y2), max(0, x1): max(0, x2)]
        if face_roi.size == 0:
            continue

        current_emb = embeddings[i]
        person_data: Dict[str, Any] = {"first_name": "Unknown", "last_name": ""}

        best_idx, best_dist = face_mgr.find_closest(current_emb)
        
        if best_idx >= 0 and best_dist < CONFIG["tolerance"]:
            person_data = persons_data[best_idx].copy()

        key = f"{person_data['first_name']}_{person_data['last_name']}"
        tracker = tracker_manager.get_or_create(
            key, person_data["first_name"], person_data["last_name"]
        )

        flicker_detected = False
        if reflector_model and skipper.should_process("reflector"):
            try:
                refl_res = reflector_model.predict(face_roi, verbose=False, conf=0.5)
                for r in refl_res:
                    if r.boxes is not None and len(r.boxes) > 0:
                        flicker_detected = True
                        break
            except Exception as e:
                logger.debug(f"Reflector error cam {cam_id}: {e}")

        emotion: Optional[str] = None
        e_conf = 0.0
        if emotion_model and skipper.should_process("emotion"):
            emotion, e_conf = detect_emotion(face_roi, emotion_model)

        tracker.add_detection(flicker_detected, emotion, e_conf)

        fl_status, fl_conf = tracker.get_flicker_status()
        dom_emotion, d_conf = tracker.get_dominant_emotion()

        person_data.update(
            {
                "flicker": fl_status,
                "flicker_confidence": fl_conf,
                "emotion": dom_emotion,
                "emotion_confidence": d_conf,
                "camera_id": cam_id,
            }
        )

        if person_data["first_name"] == "Unknown":
            color = (255, 0, 0)
        elif dom_emotion in ("Aggression",):
            color = (0, 0, 255)
        elif fl_status:
            color = (0, 255, 0)
        else:
            color = (0, 165, 255)

        cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
        labels = [f"{person_data['first_name']} {person_data['last_name']}"]
        if fl_status:
            labels.append(f"Flicker: {fl_conf:.0%}")
        if dom_emotion:
            labels.append(f"Emotion: {dom_emotion[:3]} {d_conf:.0%}")
        for j, part in enumerate(labels):
            cv2.putText(
                display,
                part,
                (x1, y1 - 10 - j * 20),
                cv2.FONT_HERSHEY_COMPLEX,
                0.6,
                color,
                1,
                cv2.LINE_AA,
            )

        if tracker.should_send_update():
            detections_to_send.append((tracker, person_data))

    return display, detections_to_send

async def send_event_data(websocket, data: dict, frame: np.ndarray):
    try:
        _, buf = cv2.imencode(".jpg", frame)
        event = {
            "type": "camera",
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "camera_id": CAMERA_ID,
            "person": data,
            "image": base64.b64encode(buf).decode("utf-8"),
        }

        if data['first_name'] != "Unknown": await websocket.send(json.dumps(event))
        logger.info(
            f"Отправка cam {CAMERA_ID}: "
            f"{data['first_name']}, emotion={data.get('emotion')}"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

async def camera_loop(
    websocket,
    face_mgr: KnownFaceManager,
    emotion_model,
    weapon_model,
    reflector_model,
    pose_model,
):
    cameras: List[CameraCapture] = []
    logger.info("Поиск доступных камер...")
    for i in range(10):
        cap = CameraCapture(i)
        if cap.is_opened():
            ok, _ = cap.read()
            if ok:
                cameras.append(cap)
                camera_manager.register_camera(i)
                logger.info(f"  ✓ Камера {i} найдена")
            else:
                cap.release()
        else:
            cap.release()

    if not cameras:
        logger.error("Не удалось открыть ни одной камеры")
        return

    logger.info(f"Активных камер: {len(cameras)}")
    for cam in cameras:
        logger.info(
            f"  http://127.0.0.1:{STREAM_PORT}/{CAMERA_ID}/camera/{cam.cam_id}/video_feed"
        )
    logger.info(
        f"  Сетка: http://127.0.0.1:{STREAM_PORT}/{CAMERA_ID}/grid"
    )

    skipper = FrameSkipper(CONFIG["skip_intervals"])
    cleanup_counter = 0

    try:
        while not shutdown_event.is_set():
            for cam in cameras:
                ok, frame = await asyncio.to_thread(cam.read)
                if not ok or frame is None:
                    continue

                processed, detections = await asyncio.to_thread(
                    process_frame,
                    frame,
                    cam.cam_id,
                    face_mgr,
                    skipper,
                    emotion_model,
                    weapon_model,
                    reflector_model,
                    pose_model,
                )

                camera_manager.update_frame(cam.cam_id, processed)

                for tracker, data in detections:
                    await send_event_data(websocket, data, frame)
                    tracker.last_sent = datetime.now()

                await asyncio.sleep(0)

            cleanup_counter += 1
            if cleanup_counter > 300:
                await asyncio.to_thread(tracker_manager.cleanup_inactive)
                cleanup_counter = 0

            if cv2.waitKey(1) & 0xFF == ord("q"):
                shutdown_event.set()
                break

            await asyncio.sleep(0.01)

    finally:
        for cam in cameras:
            cam.release()
            camera_manager.remove_camera(cam.cam_id)
        cv2.destroyAllWindows()
        logger.info("Все камеры освобождены")

async def connect_to_server(
    face_mgr, emotion_model, weapon_model, reflector_model, pose_model
):
    while not shutdown_event.is_set():
        try:
            async with websockets.connect(
                CONFIG["ws_url"],
                ping_interval=20,
                ping_timeout=60,
                max_size=None,
            ) as ws:
                logger.info("✓ Подключено к серверу")
                await ws.send(
                    json.dumps({"type": "init", "camera_id": CAMERA_ID})
                )
                await camera_loop(
                    ws, face_mgr, emotion_model, weapon_model, reflector_model, pose_model
                )
        except Exception as e:
            if shutdown_event.is_set():
                break
            logger.warning(
                f"Ошибка соединения: {e}. "
                f"Переподключение через {CONFIG['reconnect_delay']} с..."
            )
            await asyncio.sleep(CONFIG["reconnect_delay"])

async def main():
    global face_manager

    def _signal_handler(sig, _frame):
        logger.info("⏻ Получен сигнал завершения")
        shutdown_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    dev = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    logger.info(f"Устройство: {dev}")

    mtcnn_model = MTCNN(keep_all=True, device=dev)
    resnet_model = InceptionResnetV1(pretrained="vggface2").eval().to(dev)
    logger.info("✓ MTCNN + InceptionResnetV1 загружены")

    emotion_path = Path(CONFIG["paths"]["emotion_model"])
    emotion_model = YOLO(str(emotion_path)) if emotion_path.exists() else None
    if emotion_model:
        logger.info("✓ Модель эмоций загружена")
    else:
        logger.warning(f"✗ Модель эмоций не найдена: {emotion_path}")

    weapon_path = Path(CONFIG["paths"]["weapon_model"])
    weapon_model = None
    if weapon_path.exists():
        try:
            weapon_model = YOLO(str(weapon_path))
            logger.info("✓ Модель оружия загружена")
        except Exception as e:
            logger.error(f"✗ Ошибка загрузки модели оружия: {e}")
    else:
        logger.warning(f"✗ Модель оружия не найдена: {weapon_path}")

    reflector_path = Path(CONFIG["paths"]["reflector_model"])
    reflector_model = None
    if reflector_path.exists():
        try:
            reflector_model = YOLO(str(reflector_path))
            logger.info("✓ Модель рефлектора загружена")
        except Exception as e:
            logger.error(f"✗ Ошибка загрузки модели рефлектора: {e}")
    else:
        logger.warning(f"✗ Модель рефлектора не найдена: {reflector_path}")
        
    pose_path = Path(CONFIG["paths"]["pose_model"])
    pose_model = None
    if pose_path.exists():
        try:
            pose_model = YOLO(str(pose_path))
            logger.info("✓ Модель позы (Pose Estimation) загружена")
        except Exception as e:
            logger.error(f"✗ Ошибка загрузки модели позы: {e}")
    else:
        try:
            pose_model = YOLO("yolo26n-pose.pt")
            logger.info("✓ Модель позы (Pose Estimation) загружена/скачана")
        except Exception as e:
            logger.error(f"✗ Не удалось загрузить/скачать модель позы: {e}")

    face_manager = KnownFaceManager(
        CONFIG["paths"]["known_faces"], mtcnn_model, resnet_model, dev
    )
    if not face_manager.get_known_faces_list():
        logger.warning("⚠ Нет известных лиц для распознавания")

    threading.Thread(target=run_flask, daemon=True).start()
    logger.info(f"✓ API на http://0.0.0.0:{STREAM_PORT}")
    threading.Thread(target=siren_worker, daemon=True).start()

    await connect_to_server(
        face_manager, emotion_model, weapon_model, reflector_model, pose_model
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        shutdown_event.set()
        logger.info("Программа остановлена")