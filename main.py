from __future__ import annotations
import asyncio
import logging
from typing import Any, Dict, Optional
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from auth import PUBLIC_ACTIONS, check_permission
from config import settings
from database import destroy_session, get_session, init_db
from models import SessionData
import handlers
from handlers.registry import get_handler
from handlers.auth_handlers import live_websockets
import sys
import logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("smartschool")

app = FastAPI(
    title="SmartSchool Vision",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.on_event("startup")
async def startup():
    await init_db()

    for path in [
        settings.images_path,
        settings.users_path.parent,
        settings.data_path,
    ]:
        path.mkdir(parents=True, exist_ok=True)

    if not settings.users_path.exists():
        settings.users_path.write_text("[]", encoding="utf-8")

    logger.info(
        "SmartSchool Vision started on %s:%d",
        settings.app_host, settings.app_port,
    )

@app.get("/", response_class=HTMLResponse)
async def page_root():
    return FileResponse("site/index.html")


@app.get("/login", response_class=HTMLResponse)
async def page_login():
    return FileResponse("site/reg.html")


@app.get("/spisk", response_class=HTMLResponse)
async def page_spisk():
    return FileResponse("site/spisk.html")


@app.get("/camera", response_class=HTMLResponse)
async def page_camera():
    return FileResponse("site/camera.html")


@app.get("/stats", response_class=HTMLResponse)
async def page_stats():
    return FileResponse("site/stats.html")


@app.get("/grafik", response_class=HTMLResponse)
async def page_grafik():
    return FileResponse("site/grafik.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    sid_cookie = websocket.cookies.get(settings.session_cookie_name)
    sess = await get_session(sid_cookie)

    await websocket.accept()
    logger.info(
        "WS connected: %s, user=%s",
        websocket.client,
        sess.username if sess else None,
    )

    try:
        while True:
            raw = await websocket.receive_json()
            logger.info(raw)
            action = raw.get("type") or raw.get("action")
            logger.info(action)
            if not action:
                await websocket.send_json({
                    "action": "error",
                    "error": "Не указан action/type",
                })
                continue
            if sess is None:
                for sid, ws_conn in live_websockets.items():
                    if ws_conn == websocket:
                        sess = await get_session(sid)
                        if sess:
                            logger.info("Session upgraded in-flight: %s", sess.username)
                        break

            current_role = sess.role if sess else None
            if not check_permission(current_role, action):
                await websocket.send_json({
                    "action": "error",
                    "error": f"Недостаточно прав для '{action}'",
                })
                continue

            handler_func = get_handler(action)
            if handler_func is None:
                await websocket.send_json({
                    "action": "error",
                    "error": f"Неизвестное действие: {action}",
                })
                continue

            try:
                await handler_func(websocket, raw, sess)
            except Exception as e:
                logger.exception("Ошибка в обработчике '%s': %s", action, e)
                await websocket.send_json({
                    "action": "error",
                    "error": "Внутренняя ошибка сервера",
                })

            new_sid = websocket.cookies.get(settings.session_cookie_name)
            if new_sid != sid_cookie:
                sess = await get_session(new_sid)
                sid_cookie = new_sid

    except WebSocketDisconnect:
        logger.info(f"WS disconnected: {websocket.client}")
        
    except Exception as e:
        if "10054" in str(e):
            logger.info("Client disconnected abruptly (WinError 10054)")
        else:
            logger.exception(f"WS error: {e}")

    finally:
        if sess and sess.sid in live_websockets:
            del live_websockets[sess.sid]
        if sess:
            logger.info("Session ended: %s", sess.username)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        log_level=settings.log_level.lower(),
        ws="websockets",
        ws_ping_interval=20,
        ws_ping_timeout=10,
        reload=False,
    )