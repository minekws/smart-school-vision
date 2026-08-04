import sys
import os
import time
import subprocess
import requests
from PySide6.QtWidgets import QApplication, QMainWindow, QSplashScreen
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QPixmap, QImage, QIcon
from PySide6.QtCore import QUrl, Qt

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu-rasterization --enable-accelerated-video-decode --ignore-gpu-blocklist --force-light-mode --disable-features=DarkMode"

CAMERA_UI_URL = "http://127.0.0.1:5000/login"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartSchool Vision - AI Security System")
        self.resize(1366, 768)
        icon_path = os.path.abspath("icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

    def load_interface(self):
        self.browser.setUrl(QUrl(CAMERA_UI_URL))

def check_ui_is_up():
    try:
        response = requests.get(CAMERA_UI_URL, timeout=1)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def load_splash_pixmap():
    image_path = os.path.abspath(os.path.join("аи", "class.png"))
    
    if os.path.exists(image_path):
        return QPixmap(image_path)
    else:
        print(f"ОШИБКА: Картинка заставки не найдена по пути: {image_path}")
        pixmap = QPixmap(800, 500)
        pixmap.fill(Qt.darkGray)
        return pixmap


if __name__ == "__main__":
    app = QApplication(sys.argv)

    print("Загрузка картинки приветствия...")
    splash_pix = load_splash_pixmap()
    splash = QSplashScreen(splash_pix)
    splash.show()
    
    venv_python = os.path.abspath(os.path.join(".venv", "Scripts", "python.exe"))
    
    if not os.path.exists(venv_python):
        print("ОШИБКА: Не найден виртуальный каталог venv!")
        sys.exit(1)

    splash.showMessage("Запуск главного сервера...", color=Qt.white)
    app.processEvents()
    
    server_process = subprocess.Popen([venv_python, "main.py"])
    time.sleep(2) 

    splash.showMessage("Инициализация нейросетей...", color=Qt.white)
    app.processEvents()
    
    camera_script_path = os.path.join("gg.py")

    camera_process = subprocess.Popen(
        [venv_python, camera_script_path], 
        cwd="аи", 
        stdout=sys.stdout, 
        stderr=sys.stderr
    )
    splash.showMessage("Подключение к камере и ожидание интерфейса...", color=Qt.white)

    while not check_ui_is_up():
        time.sleep(0.5)
        app.processEvents() 

    window = MainWindow()
    window.load_interface()
    window.show()
    splash.finish(window)
    exit_code = app.exec()
    print("Завершение работы процессов...")
    camera_process.terminate()
    server_process.terminate()
    
    sys.exit(exit_code)