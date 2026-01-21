import requests
import json

url = "http://localhost:5000/api/generate"
payload = {
    "konu": "Paragraf",
    "alt_konu": "Ana Düşünce",
    "zorluk": "orta"
}
headers = {"Content-Type": "application/json"}

try:
    print(f"Testing {url}...")
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ SUCCESS!")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if "quality_score" in data:
            print(f"\nKalite Skoru: {data['quality_score']}")
        elif "message" in data:
            print(f"\nMesaj: {data['message']}")
    else:
        print("❌ FAILED!")
        print(response.text)

except Exception as e:
    print(f"❌ Error: {e}")
