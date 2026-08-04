# api_server.py
from fastapi import FastAPI, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import json
import os
import asyncio
import websockets
from datetime import datetime
import secrets
import logging
import traceback

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
security = HTTPBearer()

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Настройки путей
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
SITE_DIR = os.path.join(PROJECT_DIR, "site")

# Настройки
WS_SERVER_URL = "ws://192.168.1.202:8008"
API_DIR = os.path.join(PROJECT_DIR, "api")
USER_DIRS = {
    "moderator": os.path.join(PROJECT_DIR, "moderator"),
    "student": os.path.join(PROJECT_DIR, "students")
}

# Создаем необходимые директории
for directory in [API_DIR, *USER_DIRS.values()]:
    os.makedirs(directory, exist_ok=True)

# Модели данных
class UserRegister(BaseModel):
    username: str
    password: str
    role: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    email: Optional[str] = None
    cameraId: Optional[str] = None

class UserLogin(BaseModel):
    identifier: str
    password: str

# WebSocket менеджер
class WSManager:
    def __init__(self):
        self.connections = {}
        self.lock = asyncio.Lock()
        
    async def connect(self, client_id: str) -> websockets.WebSocketClientProtocol:
        """Создаём новое соединение"""
        async with self.lock:
            if client_id in self.connections and not self.connections[client_id].closed:
                return self.connections[client_id]
            
            try:
                logger.info(f"Connecting to {WS_SERVER_URL}")
                ws = await websockets.connect(WS_SERVER_URL)
                self.connections[client_id] = ws
                return ws
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                raise

    async def send_and_receive(self, data: dict) -> dict:
        """Отправка и получение данных через WebSocket"""
        client_id = f"api_{secrets.token_urlsafe(8)}"
        ws = None
        
        try:
            ws = await self.connect(client_id)
            await ws.send(json.dumps(data))
            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            return json.loads(response)
        except asyncio.TimeoutError:
            logger.error("WebSocket timeout")
            raise HTTPException(status_code=504, detail="WebSocket server timeout")
        except websockets.exceptions.ConnectionClosed:
            logger.error("WebSocket connection closed")
            raise HTTPException(status_code=503, detail="WebSocket server connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            raise HTTPException(status_code=500, detail=f"WebSocket error: {str(e)}")
        finally:
            if ws and client_id in self.connections:
                await self.close_connection(client_id)

    async def close_connection(self, client_id: str):
        """Закрываем соединение"""
        async with self.lock:
            if client_id in self.connections:
                try:
                    await self.connections[client_id].close()
                except:
                    pass
                del self.connections[client_id]

    async def cleanup(self):
        """Очистка всех соединений"""
        async with self.lock:
            for client_id in list(self.connections.keys()):
                await self.close_connection(client_id)

ws_manager = WSManager()

# Проверка токена
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    token_file = os.path.join(API_DIR, f"{token}.json")
    
    if not os.path.exists(token_file):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        with open(token_file, "r", encoding="utf-8") as f:
            token_data = json.load(f)
        return {"token": token, "data": token_data}
    except Exception as e:
        logger.error(f"Error reading token file: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

# API endpoints
@app.post("/api/register")
async def register(user: UserRegister):
    """Регистрация нового пользователя"""
    try:
        register_data = {
            "action": "register",
            "role": user.role,
            "username": user.username,
            "password": user.password
        }
        
        if user.role == "student":
            register_data.update({
                "first_name": user.firstName,
                "last_name": user.lastName,
                "email": user.email
            })
        elif user.role == "moderator":
            register_data["camera_id"] = user.cameraId
        
        response = await ws_manager.send_and_receive(register_data)
        
        if response.get("status") == "error":
            raise HTTPException(
                status_code=400, 
                detail=response.get("message", "Registration failed")
            )
        
        return {"status": "success"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=str(e)
        )

@app.post("/api/login")
async def login(user: UserLogin):
    """Авторизация пользователя"""
    try:
        # Определяем роль
        role = "student" if "@" in user.identifier else "moderator"
        username = user.identifier.split("@")[0] if "@" in user.identifier else user.identifier

        logger.info(f"Login attempt - username: {username}, role: {role}")

        # Отправляем запрос через WebSocket
        response = await ws_manager.send_and_receive({
            "action": "login",
            "role": role,
            "username": username,
            "password": user.password
        })

        logger.info(f"WebSocket response: {response}")

        if response.get("status") != "success":
            raise HTTPException(
                status_code=401, 
                detail=response.get("message", "Login failed")
            )

        # Создаем API токен
        token = secrets.token_urlsafe(32)
        token_data = {
            "username": username,  # Сохраняем username
            "role": role,
            "created_at": datetime.now().isoformat()
        }

        # Если это модератор, сохраняем camera_id дополнительно
        if role == "moderator" and response.get("camera_id"):
            token_data["camera_id"] = response["camera_id"]

        # Сохраняем токен
        token_path = os.path.join(API_DIR, f"{token}.json")
        with open(token_path, "w") as f:
            json.dump(token_data, f)

        return {
            "status": "success",
            "token": token,
            "user": {
                "username": username,  # Всегда возвращаем username
                "role": role,
                "camera_id": response.get("camera_id") if role == "moderator" else None
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для real-time обновлений"""
    await websocket.accept()
    client_id = f"ws_{secrets.token_urlsafe(8)}"
    server_ws = None
    
    try:
        # Получаем токен из первого сообщения
        try:
            auth_message = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
        except asyncio.TimeoutError:
            await websocket.send_json({"error": "Authentication timeout"})
            await websocket.close()
            return
        
        token = auth_message.get("token")
        if not token:
            await websocket.send_json({"error": "No token provided"})
            await websocket.close()
            return
        
        # Проверяем токен и получаем данные пользователя
        token_file = os.path.join(API_DIR, f"{token}.json")
        if not os.path.exists(token_file):
            await websocket.send_json({"error": "Invalid token"})
            await websocket.close()
            return
        
        # Читаем данные токена
        with open(token_file, "r", encoding="utf-8") as f:
            token_data = json.load(f)
        
        # Подключаемся к основному серверу
        server_ws = await websockets.connect(WS_SERVER_URL)
        
        # Инициализируемся на сервере с username
        await server_ws.send(json.dumps({
            "action": "init",
            "type": "web_client",
            "token": token,
            "username": token_data.get("username"),  # Передаем username
            "role": token_data.get("role"),
            "camera_id": token_data.get("camera_id")  # camera_id только если есть
        }))
        
        async def forward_to_server():
            try:
                while True:
                    data = await websocket.receive_json()
                    await server_ws.send(json.dumps(data))
            except WebSocketDisconnect:
                logger.info("Client disconnected")
            except Exception as e:
                logger.error(f"Error forwarding to server: {e}")
        
        async def forward_to_client():
            try:
                async for message in server_ws:
                    await websocket.send_text(message)
            except websockets.exceptions.ConnectionClosed:
                logger.info("Server connection closed")
            except Exception as e:
                logger.error(f"Error forwarding to client: {e}")
        
        # Запускаем обе задачи параллельно
        await asyncio.gather(
            forward_to_server(),
            forward_to_client()
        )
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if server_ws:
            await server_ws.close()
        try:
            await websocket.close()
        except:
            pass

@app.get("/api/stats/{camera_id}")
async def get_camera_stats(
    camera_id: str,
    date: Optional[str] = Query(None),
    auth=Depends(verify_token)
):
    """Получить статистику камеры"""
    try:
        if not date:
            date = datetime.now().date().isoformat()
        
        # Путь к файлу статистики
        stats_path = os.path.join(PROJECT_DIR, camera_id, date, "static.json")
        
        if not os.path.exists(stats_path):
            # Возвращаем пустую статистику если файла нет
            return {
                "camera_id": camera_id,
                "date": date,
                "stats": {
                    "camera_id": camera_id,
                    "person_total": 0,
                    "flick_total": 0,
                    "depr_total": 0,
                    "graf": {}
                }
            }
        
        with open(stats_path, "r", encoding="utf-8") as f:
            stats = json.load(f)
        
        return {
            "camera_id": camera_id,
            "date": date,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# HTML endpoints
@app.get("/", response_class=HTMLResponse)
async def get_login_page():
    """Страница входа"""
    reg_path = os.path.join(SITE_DIR, "reg.html")
    if os.path.exists(reg_path):
        with open(reg_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>reg.html not found</h1>", status_code=404)

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard_page():
    """Страница панели управления"""
    site_path = os.path.join(SITE_DIR, "site.html")
    if os.path.exists(site_path):
        with open(site_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>site.html not found</h1>", status_code=404)

# Статические файлы
@app.get("/ima/{file_path:path}")
async def get_ima_file(file_path: str):
    """Обработка файлов из папки ima"""
    file_location = os.path.join(SITE_DIR, "ima", file_path)
    if os.path.exists(file_location):
        return FileResponse(file_location)
    else:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

@app.get("/static/{file_path:path}")
async def get_static_file(file_path: str):
    """Обработка статических файлов"""
    file_location = os.path.join(SITE_DIR, file_path)
    if os.path.exists(file_location):
        return FileResponse(file_location)
    else:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

# Cleanup при завершении
@app.on_event("shutdown")
async def shutdown_event():
    """Закрываем все соединения при остановке сервера"""
    await ws_manager.cleanup()

if __name__ == "__main__":
    import uvicorn
    print(f"Starting API server on http://localhost:8000")
    print(f"Project structure:")
    print(f"  Base dir (аи): {BASE_DIR}")
    print(f"  Project dir: {PROJECT_DIR}")
    print(f"  Site dir: {SITE_DIR}")
    print(f"  API dir: {API_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8000)