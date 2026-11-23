<h1 align="center">SmartSchool Vision</h1>

<p align="center">
  <strong>Local computer vision for classroom attendance</strong><br>
  An OpenCV and YOLO camera runtime sends events to a FastAPI dashboard over WebSockets.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-WebSocket-009688?logo=fastapi&logoColor=white">
  <img alt="Vision" src="https://img.shields.io/badge/OpenCV%20%2B%20YOLO-Computer%20Vision-5C3EE8?logo=opencv&logoColor=white">
  <img alt="Graphify" src="https://img.shields.io/badge/Architecture-Graphify-111827">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-2EA44F">
</p>

## Entrance demo

[![SmartSchool Vision showing YOLO pose, an expression label, and the web dashboard](demo/entrance-live.jpg)](https://github.com/minekws/smart-school-vision/releases/download/entrance-demo/SmartSchool-Vision-Live-Demo.mp4)

[**Download the 20-second demo · 1080p MP4**](https://github.com/minekws/smart-school-vision/releases/download/entrance-demo/SmartSchool-Vision-Live-Demo.mp4)

The demo feeds recorded entrance footage through the project's local camera service and FastAPI backend. The camera draws YOLO pose landmarks and labels visible facial expressions. The backend receives two recognition events over WebSocket and shows the fictional names in the web dashboard.

- **0:00** Close-up of the camera output with pose landmarks and an expression label.
- **0:02** Camera output alongside controls and recent detections from the web interface.
- **0:08** The main dashboard displays both saved recognition events.
- **0:14** A separate test image triggers a weapon-detection box and a critical log entry. The edit reproduces the application’s siren tones.

Entrance footage by [PNW Production on Pexels](https://www.pexels.com/video/men-passing-by-door-8275796/). Test image by [Lou Rivera, U.S. Department of Defense](https://commons.wikimedia.org/wiki/File:DA-SC-92-01299.jpg).

> [!IMPORTANT]
> This repository is an educational prototype and research-oriented platform. It is not a medical, disciplinary, or production surveillance product. Any deployment involving minors, biometrics, emotion inference, or safety alerts must include consent, legal review, human oversight, retention limits, and a documented governance process.

## Overview

SmartSchool Vision is a modular vision-driven school operations system built around a FastAPI control plane, a local camera runtime, and a browser dashboard. The project combines classroom attendance analytics, role-aware event processing, and a local edge AI runtime for people, pose, object, and safety detection.

### What the project does

- Real-time camera capture with reconnect and frame-skipping logic
- Local face matching against a managed known-faces gallery
- YOLO-based detection for reflectors, pose, safety events, and emotion signals
- WebSocket event ingestion and centralized handler routing
- Attendance, roster, schedule, and analytics views in one control plane
- Desktop launchers for edge-first local operation
- Secure session handling and atomic JSON updates

## Architecture

```text
Camera / RTSP / webcam
        |
        v
Edge vision runtime (:5000)
  OpenCV + YOLO + Face recognition
        |  WebSocket events + MJPEG frames
        v
FastAPI control plane (:8005)
  auth -> registry -> handlers -> services
        |                           |
        v                           v
SQLite sessions               JSON storage / analytics
        |
        v
Dashboard / team tools / attendance / schedule
```

## Graphify Analysis

A Graphify pass over the source code produced a strong architectural map:

- 364 nodes
- 774 edges
- 22 communities
- 0 import cycles detected

The highest-value architectural hubs are:

- `SessionData`
- `handle_register()`
- `read_json_safe()`
- `process_frame()`
- `handle_camera_event()`
- `update_json_atomic()`
- `sanitize_camera_id()`
- `KnownFaceManager`

Graphify also highlights a useful architectural insight: the two large vision runtimes are currently the most cohesive candidates for future refactoring into cleaner capture, inference, tracking, alerting, and transport layers.

### Graphify artifacts

- [Open interactive architecture graph](graphify-out/graph.html)
- [Read the architecture report](graphify-out/GRAPH_REPORT.md)
- [Explore graph JSON export](graphify-out/graph.json)

## Repository Structure

```text
handlers/       WebSocket action handlers
services/       Users, cameras, stats, storage services
utils/          Security and path utilities
site/           Server-rendered HTML entry points
static/         Frontend assets and UI scripts
aи/             Edge AI runtime and launcher layer
graphify-out/   Visual architecture graph and analysis
main.py         FastAPI backend entry point
launcher.py     Desktop launcher entry point
```

## Quick Start

### Windows executables

Download the Windows x64 [server](https://github.com/minekws/smart-school-vision/releases/download/entrance-demo/SmartSchoolVision-Server.exe) and [camera](https://github.com/minekws/smart-school-vision/releases/download/entrance-demo/SmartSchoolVision-Camera.exe). Start the server first, then start the camera. The executables share a local data directory at `%LOCALAPPDATA%\SmartSchoolVision`.

- Open the [main site](http://127.0.0.1:8005/login) and register a moderator with camera ID `01` for a fresh installation.
- Open the [camera dashboard](http://127.0.0.1:5000/01/dashboard) to see the local stream. The camera executable runs on CPU and downloads the FaceNet and pose checkpoints on first use.
- To replay a file, run `./SmartSchoolVision-Camera.exe --video "C:\Videos\entrance.mp4"` in PowerShell. Use `Ctrl+C` in each console to stop the processes.

To use your existing optional emotion, reflector, or weapon weights, place a `.env` file in the shared data directory with `EMOTION_MODEL`, `REFLECTOR_MODEL`, and `WEAPON_MODEL` set to the local paths. The build instructions and bundled dependency notices are in [windows_bundle](windows_bundle/README.md).

### Run from source

### 1) Backend + dashboard

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
```

Then open:

- `http://127.0.0.1:8005/login`

### 2) Full edge runtime

```powershell
python -m pip install -r requirements-ai.txt
python launcher.py
```

The edge service expects the main backend on port `8005` and exposes its local camera interface on port `5000`.

## Configuration

Copy `.env.example` to `.env` and configure the environment for your local deployment.

| Variable | Purpose |
| --- | --- |
| `APP_PORT` | FastAPI control-plane port |
| `FACE_API_BASE` | Edge vision HTTP endpoint |
| `KNOWN_FACES_DIR` | Private local gallery for face embeddings |
| `REFLECTOR_MODEL` | Object detector weights |
| `EMOTION_MODEL` | Emotion model weights |
| `WEAPON_MODEL` | Safety-event model weights |
| `POSE_MODEL` | Pose model weights |

## Privacy and Security Notes

- Passwords are hashed with bcrypt.
- Sessions are stored with random URL-safe identifiers and expiry.
- WebSocket actions pass through centralized role checks.
- Camera identifiers are sanitized before filesystem use.
- Sensitive runtime artifacts are excluded through `.gitignore`.

> Before production use, add TLS, secrets management, retention/deletion policy, audit logging, rate limiting, and formal human oversight.

## Development Notes

The project still includes research artifacts and alternate AI scripts. The recommended next step is to consolidate the duplicated vision runtimes, abstract the model adapters behind interfaces, and move operational storage onto a migration-managed database.

Run a syntax check without starting the camera stack:

```powershell
python -m compileall -q .
```

## License

Released under the [MIT License](LICENSE). Model weights, datasets, training assets, and third-party media are not bundled in this repository and may be governed by separate terms.

