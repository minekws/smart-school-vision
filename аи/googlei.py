import os
from pathlib import Path

import google.generativeai as genai
import PIL.Image

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("Set GOOGLE_API_KEY before running this experiment")

genai.configure(api_key=GOOGLE_API_KEY)

# Сначала проверим доступные модели
print("Доступные модели:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"  - {m.name}")

print("-" * 50)

# Попробуй эти модели по очереди
model_options = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro-latest", 
    "gemini-1.5-pro",
    "gemini-pro-vision",
    "gemini-1.0-pro-vision-latest",
]

image_path = Path(os.environ.get("GEMINI_IMAGE_PATH", "input.webp"))
img = PIL.Image.open(image_path)

for model_name in model_options:
    try:
        print(f"Пробую модель: {model_name}")
        model = genai.GenerativeModel(model_name)
        
        response = model.generate_content([
            "Посмотри на это фото. Перечисли продукты, которые ты видишь. "
            "Затем придумай 2 простых рецепта на русском языке, используя эти продукты.", 
            img
        ])
        
        print(f"✅ Работает: {model_name}")
        print(response.text)
        break
        
    except Exception as e:
        print(f"❌ {model_name}: {str(e)[:50]}...")
        continue