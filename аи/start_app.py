import subprocess
import time
import socket
import sys
import threading
import webview
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = PROJECT_ROOT / "main.py"
CAMERA_SCRIPT = PROJECT_ROOT / "аи" / "gg.py"
     
PORT = 5000 
DASHBOARD_URL = f"http://127.0.0.1:{PORT}/login"

LAUNCHER_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>SmartVision AI Edge Node</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">  
    <style>
        :root {
            --gray-50: #f9fafb;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-500: #6b7280;
            --gray-800: #1f2937;
            --blue-400: #60a5fa;
            --blue-600: #2563eb;
            --blue-700: #1d4ed8;
            --red-100: #fee2e2;
            --red-600: #dc2626;
            --yellow-100: #fef3c7;
            --yellow-600: #d97706;
        }

        body {
            background-image: url("https://img.freepik.com/premium-photo/blackboard-desks-chairs-empty-school-classroom-3d-rendering_651547-1438.jpg?semt=ais_items_boosted&w=740");
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-size: cover;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            user-select: none;
            
        }

        .app-card {
            background-color: #ffffff;
            padding: 2.5rem; /* p-10 */
            border-radius: 1.5rem; /* rounded-3xl */
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); /* shadow-xl */
            text-align: center;
            max-width: 28rem; /* max-w-md */
            width: 100%;
            border: 1px solid var(--gray-200);
            box-sizing: border-box;
        }

        .app-icon {
            width: 5rem;
            height: 5rem;

            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.25rem;
            margin: 0 auto 1.5rem auto;
        }

        .app-title {
            font-size: 1.875rem; /* text-3xl */
            font-weight: 900; /* font-black */
            color: var(--gray-800);
            letter-spacing: -0.025em;
            margin: 0;
        }

        .app-subtitle {
            color: var(--gray-500);
            font-weight: 500;
            font-size: 0.875rem; /* text-sm */
            margin: 0.5rem 0 2rem 0;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        /* --- Панель статусов --- */
        .status-panel {
            background-color: var(--gray-50);
            padding: 1rem;
            border-radius: 0.75rem;
            margin-bottom: 2rem;
            border: 1px solid var(--gray-100);
            display: flex;
            flex-direction: column;
            gap: 0.5rem; /* space-y-2 */
        }

        .status-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .status-name {
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--gray-500);
            text-transform: uppercase;
        }

        /* --- Бейджи (Индикаторы) --- */
        .badge {
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.1em;
            display: inline-flex;
            align-items: center;
        }

        .badge-offline {
            background-color: var(--red-100);
            color: var(--red-600);
        }

        .badge-loading {
            background-color: var(--yellow-100);
            color: var(--yellow-600);
        }

        /* --- Кнопка запуска --- */
        .btn-start {
            width: 100%;
            background-color: var(--blue-600);
            color: #ffffff;
            font-weight: 700;
            padding: 1rem 0;
            border-radius: 0.75rem;
            transition: background-color 0.2s, box-shadow 0.2s;
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            border: none;
            cursor: pointer;
            font-size: 1rem;
        }

        .btn-start:hover:not(:disabled) {
            background-color: var(--blue-700);
        }

        /* Стили для состояния загрузки (disabled) */
        .btn-start:disabled, 
        .btn-start.is-loading {
            background-color: var(--blue-400);
            cursor: not-allowed;
            box-shadow: none;
        }
    </style>
</head>
<body>
    <div class="app-card">
        <svg class="app-icon" width="42" height="47" viewBox="0 0 42 47" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M20.1432 1.00361C19.2464 1.39423 10.8229 4.92685 8.8281 5.75056C8.11567 6.04778 7.24398 6.41293 6.90034 6.56578C6.31363 6.82903 6.28848 6.84601 6.48126 6.93093C7.99833 7.57631 13.4715 9.82666 13.5469 9.82666C13.5637 9.82666 13.6056 9.61436 13.6308 9.35961C13.7984 7.71218 15.173 6.49785 17.503 5.95437C18.073 5.8185 18.5172 5.79302 20.4785 5.79302C22.6577 5.80151 22.8421 5.81001 23.8479 6.03079C25.6751 6.42142 26.6809 6.87998 27.4436 7.64425C27.8711 8.08583 28.265 8.86708 28.3321 9.41056C28.3572 9.63984 28.3991 9.82666 28.4243 9.82666C28.4494 9.82666 28.9607 9.62286 29.5642 9.3681C30.1676 9.11334 31.735 8.45947 33.0509 7.91599C34.3668 7.37251 35.4899 6.89697 35.5486 6.863C35.624 6.82054 35.557 6.7526 35.3391 6.66768C34.1405 6.17516 26.9407 3.16054 22.8924 1.45368C21.8447 1.0121 20.9814 0.655441 20.9646 0.655441C20.9479 0.655441 20.5791 0.816786 20.1432 1.00361Z" fill="black"/>
        <path d="M5.2911 5.35125L3.54773 6.04759V8.23V10.4209L3.76565 10.336C4.04224 10.2256 4.60381 10.2256 4.81335 10.336C4.9726 10.4209 4.9726 10.3699 4.9726 8.06016V5.69942L6.06221 5.20689C7.05961 4.74833 7.26915 4.63793 7.09314 4.65492C7.05123 4.65492 6.2466 4.96912 5.2911 5.35125Z" fill="black"/>
        <path d="M6.23821 9.60579L5.28271 10.5654L5.50901 10.8966L5.72693 11.2277V13.6649V16.1106H4.21825H2.70956L2.70118 15.2359L2.6928 14.3697L2.16476 15.4737C0.949427 17.9788 0.312426 20.6197 0.220229 23.5409C0.0358339 29.4088 2.12285 34.7247 6.22145 38.8688C8.02349 40.6775 9.5657 41.79 11.8874 42.9449C13.7733 43.8875 15.634 44.5074 17.5953 44.847C18.1987 44.9574 18.3664 45.0169 18.4669 45.1697C18.6849 45.5264 19.2213 46.0019 19.6655 46.2397C20.0594 46.4435 20.1852 46.469 20.9395 46.469C21.6855 46.469 21.828 46.4435 22.2554 46.2312C22.5488 46.0869 22.9092 45.7981 23.2025 45.4754L23.6719 44.9659L24.8621 44.7197C29.7318 43.7431 34.0316 41.1616 37.0908 37.3912C39.488 34.436 40.9883 31.0647 41.575 27.3113C41.7929 25.9187 41.7929 22.403 41.575 21.0783C41.3571 19.779 40.9212 18.1061 40.5189 17.0107C39.8568 15.2274 38.5744 12.9431 37.4261 11.4825C36.8645 10.7777 35.5989 9.42746 35.0541 8.9689L34.6602 8.63771L32.4977 9.53785C31.2992 10.0389 29.891 10.6163 29.363 10.8371L28.3991 11.2362L28.374 12.3147C28.3656 12.9091 28.3405 13.3932 28.3321 13.3932C28.3153 13.3932 27.9381 13.1469 27.4855 12.8497C26.0774 11.8986 24.267 11.2447 22.4566 11.0154C21.4424 10.8796 19.5985 10.9475 18.6765 11.1428C17.1678 11.457 15.5418 12.1364 14.2342 13.0025L13.6475 13.3847L13.6056 12.3147L13.5637 11.2362L12.8094 10.9305C12.3987 10.7522 10.9822 10.1662 9.67466 9.62277C8.37551 9.07929 7.27753 8.63771 7.244 8.63771C7.21885 8.64621 6.76625 9.07929 6.23821 9.60579ZM22.5991 12.8412C26.4127 13.4186 29.7318 16.3313 30.8717 20.1017C31.2321 21.2906 31.3159 21.885 31.3159 23.1588C31.3075 24.8742 30.9639 26.3772 30.2179 27.8718C29.7821 28.755 29.363 29.3409 28.4075 30.4194C27.7537 31.1497 27.4604 31.5573 27.2006 32.0923C26.8066 32.9075 26.3289 34.2832 26.1864 34.9795C26.002 35.8711 26.3708 35.8117 21.0485 35.8117C15.7345 35.8117 16.0363 35.8542 15.8267 35.0644C15.525 33.935 15.1814 32.9669 14.8126 32.2027C14.5025 31.5403 14.2678 31.2176 13.6643 30.5637C12.6753 29.4853 12.1724 28.755 11.6192 27.6086C9.23044 22.6153 11.3175 16.4927 16.2877 13.9112C17.4947 13.2828 18.5759 12.9431 19.8499 12.7733C20.4701 12.6883 21.8447 12.7223 22.5991 12.8412ZM33.7047 13.1044C33.8304 13.1894 33.8891 13.3167 33.8891 13.5036C33.8891 13.7498 33.7717 13.8942 32.9922 14.633C31.7182 15.8388 31.2992 16.1955 31.1567 16.1955C30.9639 16.1955 30.7041 15.8728 30.7041 15.6265C30.7041 15.4482 30.922 15.1934 31.7685 14.3782C32.8665 13.3082 33.2688 12.9686 33.4281 12.9686C33.4784 12.9686 33.6041 13.028 33.7047 13.1044ZM10.077 14.2508C11.3761 15.4907 11.4851 15.6435 11.2001 15.9577C10.9235 16.2719 10.6385 16.1615 9.85905 15.4142C8.14921 13.8093 8.07378 13.7243 8.07378 13.4866C8.07378 13.1809 8.21626 13.0535 8.54315 13.0535C8.76945 13.0535 8.99575 13.2318 10.077 14.2508ZM36.2778 17.7665C36.7556 18.242 36.5125 18.4458 34.5931 19.1676C33.7047 19.4903 32.9084 19.7621 32.8162 19.7621C32.6151 19.7621 32.3804 19.4648 32.3804 19.2016C32.3804 18.9214 32.5899 18.794 33.9729 18.2845C34.6853 18.0212 35.4061 17.7495 35.5654 17.6816C35.9761 17.5202 36.0431 17.5287 36.2778 17.7665ZM7.81395 18.2335C8.71078 18.5562 9.4735 18.8704 9.51541 18.9299C9.6998 19.2356 9.4735 19.7621 9.155 19.7621C8.96222 19.7621 5.81913 18.6072 5.66826 18.4798C5.51739 18.3524 5.52577 17.9363 5.69341 17.775C5.76046 17.6985 5.90295 17.6391 6.00352 17.6391C6.1041 17.6391 6.9255 17.9023 7.81395 18.2335ZM8.62696 22.7172C8.93708 22.921 8.9287 23.49 8.61858 23.6174C8.54315 23.6428 7.6547 23.6683 6.64052 23.6683C4.91392 23.6683 4.79658 23.6598 4.63733 23.4985C4.54513 23.4051 4.46969 23.2522 4.46969 23.1588C4.46969 23.0654 4.54513 22.9125 4.63733 22.8191C4.79658 22.6578 4.91392 22.6493 6.67405 22.6493C7.6966 22.6493 8.57667 22.6833 8.62696 22.7172ZM37.2836 22.7682C37.3758 22.8361 37.4345 22.989 37.4345 23.1588C37.4345 23.6428 37.3339 23.6683 35.2972 23.6683C33.5789 23.6683 33.4616 23.6598 33.3024 23.4985C33.1012 23.2947 33.0844 23.0144 33.2772 22.8022C33.4029 22.6663 33.5789 22.6493 35.272 22.6493C36.7053 22.6493 37.1579 22.6748 37.2836 22.7682ZM9.46512 26.8528C9.62437 27.1075 9.5657 27.4472 9.3394 27.5746C8.93708 27.7869 6.04543 28.7719 5.8778 28.7465C5.77722 28.7295 5.63473 28.6191 5.5593 28.4832C5.45034 28.2794 5.45034 28.2285 5.5593 28.0331C5.65988 27.8463 5.96162 27.7105 7.27753 27.2349C8.15759 26.9122 8.97061 26.649 9.09633 26.649C9.25558 26.6405 9.37292 26.7084 9.46512 26.8528ZM34.5344 27.184C35.3726 27.4897 36.1353 27.7784 36.2275 27.8293C36.5712 28.0077 36.5209 28.6021 36.1605 28.721C35.9509 28.7889 32.7408 27.685 32.5312 27.4727C32.2463 27.184 32.4391 26.6405 32.833 26.6405C32.9336 26.6405 33.6963 26.8867 34.5344 27.184ZM11.1582 30.3939C11.2169 30.4533 11.2588 30.6147 11.2588 30.759C11.2588 30.9798 11.0911 31.1751 10.0434 32.1857C9.04604 33.1368 8.78621 33.3491 8.58505 33.3491C8.32522 33.3491 8.07378 33.0943 8.07378 32.8395C8.07378 32.7207 8.86165 31.8969 10.0602 30.776C10.5883 30.2835 10.9319 30.1646 11.1582 30.3939ZM32.657 31.4893C33.7885 32.5848 33.8974 32.7122 33.8723 32.9584C33.8472 33.2472 33.5454 33.4594 33.3024 33.366C33.2185 33.3321 32.6067 32.7886 31.9362 32.1602C30.6789 30.9883 30.5867 30.844 30.7879 30.4533C30.8465 30.3429 30.9639 30.292 31.1483 30.292C31.383 30.292 31.5841 30.4533 32.657 31.4893ZM25.7925 37.5271C25.9685 37.7818 25.9601 37.9601 25.7673 38.1979L25.6081 38.4017L20.973 38.3932L16.3464 38.3847L16.1872 38.1979C16.0028 37.9601 15.9944 37.7733 16.1704 37.5271L16.2961 37.3402H20.9814H25.6667L25.7925 37.5271ZM25.7422 39.9897C25.8846 40.1341 25.8679 41.2974 25.7086 41.8409C25.6081 42.1721 25.4656 42.4014 25.1471 42.7241C24.4095 43.4544 24.3592 43.4629 20.8473 43.4374C17.8802 43.4119 17.8299 43.4119 17.4612 43.2166C16.5224 42.7156 16.1452 42.0108 16.1117 40.6775C16.1033 40.3548 16.1369 40.1001 16.2039 40.0152C16.2961 39.9048 16.8828 39.8878 20.973 39.8878C24.4933 39.8878 25.6667 39.9133 25.7422 39.9897Z" fill="black"/>
        <path d="M17.2433 41.3058C17.3271 41.7474 17.5283 42.0191 17.9725 42.2484C18.3413 42.4352 18.3664 42.4437 21.124 42.4182C23.7893 42.3928 23.915 42.3843 24.1413 42.2144C24.4766 41.9597 24.7532 41.5181 24.7532 41.2379V40.9916H20.9731H17.193L17.2433 41.3058Z" fill="black"/>
        </svg>
        <h1 class="app-title">SmartVision</h1>
        <p class="app-subtitle">AI Security Edge Node</p>
        
        <div class="status-panel">
            <div class="status-row">
                <span class="status-name">WS Сервер (8005)</span>
                <span id="ws-badge" class="badge badge-offline">
                    <i class="fa-solid fa-circle-xmark mr-1"></i> OFFLINE
                </span>
            </div>
            <div class="status-row">
                <span class="status-name">Камера и ИИ (5000)</span>
                <span id="ai-badge" class="badge badge-offline">
                    <i class="fa-solid fa-circle-xmark mr-1"></i> OFFLINE
                </span>
            </div>
        </div>

        <button id="start-btn" onclick="startSystem()" class="btn-start">
            <i class="fa-solid fa-power-off"></i> Запустить систему
        </button>
    </div>

    <script>
        function startSystem() {
            const btn = document.getElementById('start-btn');
            const wsBadge = document.getElementById('ws-badge');
            const aiBadge = document.getElementById('ai-badge');
            
            // UI обновления стали намного чище
            btn.disabled = true;
            btn.classList.add('is-loading');
            btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Запуск компонентов...';
            
            // Меняем класс бейджей на "badge-loading"
            wsBadge.className = "badge badge-loading";
            wsBadge.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> STARTING';
            
            aiBadge.className = "badge badge-loading";
            aiBadge.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> LOADING AI';

            // Даем команду Python запустить файлы
            if (typeof pywebview !== 'undefined') {
                pywebview.api.trigger_start().then(() => {
                    let checkInterval = setInterval(() => {
                        pywebview.api.check_server().then((isReady) => {
                            if (isReady) {
                                clearInterval(checkInterval);
                                window.location.href = "http://127.0.0.1:5000/login";
                                pywebview.api.start_monitoring();
                            }
                        });
                    }, 1000);
                });
            } else {
                console.warn("pywebview не найден. Код запущен вне среды приложения.");
            }
        }
    </script>
</body>
</html>
"""

def is_server_running(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

class JSBridge:
    def __init__(self):
        self._window = None  
        self.server_process = None
        self.camera_process = None

    def trigger_start(self):
        """Запускает процессы в фоне"""
        print("[Лаунчер] Запуск WS сервера...")
        if self.server_process is None or self.server_process.poll() is not None:
            self.server_process = subprocess.Popen([sys.executable, str(SERVER_SCRIPT)])
        
        time.sleep(1)
        
        print("[Лаунчер] Запуск модуля ИИ и камеры...")
        if self.camera_process is None or self.camera_process.poll() is not None:
            self.camera_process = subprocess.Popen(
                [sys.executable, str(CAMERA_SCRIPT)], cwd=CAMERA_SCRIPT.parent
            )
        
        return True

    def check_server(self):
        return is_server_running(PORT)

    def start_monitoring(self):
        """Фоновый мониторинг: если gg.py выключен через интерфейс, возвращаем экран Лаунчера"""
        def monitor():
            time.sleep(5)
            while True:
                time.sleep(2)
                if not is_server_running(PORT):
                    print("[Лаунчер] ИИ сервер остановлен. Возврат в меню.")
                    self.stop_all()
                    self._window.evaluate_js("window.location.reload();")
                    break
        threading.Thread(target=monitor, daemon=True).start()

    def stop_all(self):
        """Убивает оба процесса"""
        if self.camera_process:
            self.camera_process.terminate()
            self.camera_process = None
        if self.server_process:
            self.server_process.terminate()
            self.server_process = None

def main():
    api = JSBridge()
    window = webview.create_window(
        title='SmartVision System Launcher', 
        html=LAUNCHER_HTML, 
        js_api=api,
        width=1024, 
        height=768,
        min_size=(1024, 768)
    )
    api._window = window # Передаем окно безопасно
    webview.start()
    
    # Если закрыли крестиком:
    api.stop_all()
    sys.exit(0)

if __name__ == '__main__':
    main()