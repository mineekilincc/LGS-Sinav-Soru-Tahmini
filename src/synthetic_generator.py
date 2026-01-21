# -*- coding: utf-8 -*-
"""
SENTETİK VERİ ÜRETİCİ V3 - INCREMENTAL SAVE
============================================
Groq API - Her başarılı üretimde kaydet (rate limit koruması)
"""

import json
import re
import time
import os
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv
import requests

script_dir = Path(__file__).parent
project_dir = script_dir.parent
load_dotenv(project_dir / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

ALT_KONU_SABLONLARI = {
    "Çok Anlamlılık": {"aciklama": "Bir sözcük farklı cümlelerde farklı anlamlarda kullanılır."},
    "Deyim": {"aciklama": "Deyimler kalıplaşmış söz öbekleridir."},
    "Sebep-Sonuç": {"aciklama": "Bir olayın nedeni veya sonucu sorulur."},
    "Fiilimsiler": {"aciklama": "Fiil kökünden türeyen isim, sıfat veya zarf gibi sözcükler."},
    "Noktalama": {"aciklama": "Noktalama işaretlerinin doğru kullanımı."},
    "Öznel-Nesnel": {"aciklama": "Öznel yargı kişisel görüş, nesnel yargı kanıtlanabilir bilgi."},
    "Anlatım Biçimi": {"aciklama": "Öyküleme, betimleme, açıklama veya tartışma."},
    "Koşul": {"aciklama": "Koşul anlamı taşıyan cümleler: -sa/-se, eğer."},
    "Yazım Yanlışı": {"aciklama": "TDK yazım kurallarına uygunluk."},
    "Ana Düşünce": {"aciklama": "Metnin ana fikri."},
    "Başlık Bulma": {"aciklama": "Metnin içeriğine uygun başlık."},
}

TEMALAR = ["Teknoloji", "Çevre", "Sağlık", "Okuma", "Bilim", "Spor", "İletişim"]

def count_words(text):
    return len(re.findall(r'\b\w+\b', text or "", re.UNICODE))

def call_groq(prompt):
    """Groq API çağrısı - tek deneme."""
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "max_tokens": 1200,
        }
        response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        elif response.status_code == 429:
            return "RATE_LIMIT"
        else:
            return None
    except:
        return None

def get_konu(alt_konu):
    mapping = {
        "Ana Düşünce": "Paragraf", "Başlık Bulma": "Paragraf", "Anlatım Biçimi": "Paragraf",
        "Sebep-Sonuç": "Cümlede Anlam", "Koşul": "Cümlede Anlam", "Öznel-Nesnel": "Cümlede Anlam",
        "Deyim": "Cümlede Anlam", "Fiilimsiler": "Dil Bilgisi", "Çok Anlamlılık": "Sözcükte Anlam",
        "Noktalama": "Yazım Kuralları", "Yazım Yanlışı": "Yazım Kuralları",
    }
    return mapping.get(alt_konu, "Paragraf")

def generate_one(alt_konu):
    """Tek soru üret."""
    import random
    tema = random.choice(TEMALAR)
    aciklama = ALT_KONU_SABLONLARI.get(alt_konu, {}).get("aciklama", "")
    
    prompt = f"""Sen MEB LGS 8. sınıf Türkçe soru yazarısın.

GÖREV: {alt_konu} konusunda LGS sorusu yaz.
KONU AÇIKLAMASI: {aciklama}
TEMA: {tema}

KURALLAR:
1. SADECE TÜRKÇE yaz!
2. Metin EN AZ 80 kelime, EN FAZLA 150 kelime olmalı!
3. Paragraf şeklinde yaz, numaralı cümle KULLANMA!
4. 4 şık olmalı (A, B, C, D)
5. Doğru cevabı belirt

ÇIKTI (TAM BU JSON FORMATINDA):
{{"metin": "80-150 kelimelik uzun paragraf buraya", "soru": "Soru metni", "sik_a": "A şıkkı", "sik_b": "B şıkkı", "sik_c": "C şıkkı", "sik_d": "D şıkkı", "dogru_cevap": "A"}}

SADECE JSON döndür!"""

    response = call_groq(prompt)
    
    if response == "RATE_LIMIT":
        return "RATE_LIMIT"
    if not response:
        return None
    
    try:
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1:
            data = json.loads(response[start:end+1])
            metin = data.get("metin", "")
            wc = count_words(metin)
            
            # Daha esnek kelime aralığı: 40-200
            if 40 <= wc <= 200:
                return {
                    "user": f"Konu: {get_konu(alt_konu)}\nAlt Konu: {alt_konu}",
                    "assistant": json.dumps(data, ensure_ascii=False),
                    "wc": wc
                }
    except:
        pass
    return None

def run_generator(train_path, output_path, target_per_alt=5):
    """Ana döngü - incremental save."""
    
    # Mevcut sayıları hesapla
    data = []
    with open(train_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data.append(json.loads(line.strip()))
            except:
                pass
    
    counts = Counter()
    for ex in data:
        user = ex.get("user", "")
        if "Alt Konu:" in user:
            ak = user.split("Alt Konu:")[1].split("\n")[0].strip()
            counts[ak] += 1
    
    # Eksikleri belirle
    print(f"{'='*50}")
    print(f"MEVCUT DURUM:")
    needs = {}
    for ak in ALT_KONU_SABLONLARI:
        c = counts.get(ak, 0)
        need = max(0, target_per_alt)
        needs[ak] = need
        print(f"   {ak}: {c}")
    
    # Üretim
    print(f"\n{'='*50}")
    print(f"ÜRETİM (her alt konu için {target_per_alt})")
    
    generated = []
    
    for alt_konu in ALT_KONU_SABLONLARI:
        print(f"\n📝 {alt_konu}:")
        success = 0
        attempts = 0
        max_attempts = target_per_alt * 5
        
        while success < target_per_alt and attempts < max_attempts:
            attempts += 1
            result = generate_one(alt_konu)
            
            if result == "RATE_LIMIT":
                print(f"   ⏳ Rate limit, 10sn bekleniyor...")
                time.sleep(10)
                continue
            
            if result:
                generated.append(result)
                success += 1
                print(f"   ✅ {success}/{target_per_alt} ({result['wc']} kelime)")
                
                # Her başarılı üretimde kaydet
                with open(output_path, 'a', encoding='utf-8') as f:
                    save = {"user": result["user"], "assistant": result["assistant"]}
                    f.write(json.dumps(save, ensure_ascii=False) + '\n')
            
            time.sleep(1)  # Rate limit koruması
        
        print(f"   Tamamlandı: {success}/{target_per_alt}")
    
    print(f"\n{'='*50}")
    print(f"✅ TOPLAM: {len(generated)} örnek üretildi")
    print(f"   Kaydedildi: {output_path}")

if __name__ == "__main__":
    train_path = project_dir / "data" / "v11_filtered" / "train.jsonl"
    output_path = project_dir / "data" / "synthetic_v1.jsonl"
    
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY bulunamadı!")
        exit(1)
    
    # Eski dosyayı temizle
    if output_path.exists():
        output_path.unlink()
    
    print(f"🔑 Groq API: ...{GROQ_API_KEY[-8:]}")
    
    # Her alt konu için 5 örnek üret (toplam ~55)
    run_generator(train_path, output_path, target_per_alt=5)
