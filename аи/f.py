from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

url = "https://www.binance.com/ru/trade/BTC_USDT?type=spot"

try:
    # Настройка Selenium с автоматической установкой ChromeDriver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Фоновый режим
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    
    # Ожидание загрузки (опционально)
    driver.implicitly_wait(5)  # Ждём до 5 секунд
    
    title = driver.title
    print(f"Заголовок страницы: {title}")
    
    driver.quit()
    
except Exception as e:
    print(f"Ошибка: {e}")