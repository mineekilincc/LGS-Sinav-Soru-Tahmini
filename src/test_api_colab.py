import os
import requests
import json
from dotenv import load_dotenv

# Load .env
load_dotenv()

API_URL = os.getenv("COLAB_API_URL")
print(f"🔗 Test edilecek URL: {API_URL}")

if not API_URL:
    print("❌ COLAB_API_URL bulunamadı!")
    exit(1)

full_url = f"{API_URL}/generate"

payload = {
    "prompt": {
        "user": "Konu: Paragraf\nAlt Konu: Ana Düşünce\nZorluk: Kolay\nSoru üret."
    }
}

print("⏳ İstek gönderiliyor...")
try:
    response = requests.post(full_url, json=payload, timeout=120)  # 2 dakika (ilk request uzun sürebilir)
    
    print(f"📡 Status Code: {response.status_code}")
    if response.status_code == 200:
        print("✅ Başarılı! Cevap:")
        print(response.json())
    else:
        print("❌ Hata! Cevap:")
        print(response.text)

except Exception as e:
    print(f"❌ Bağlantı hatası: {e}")
