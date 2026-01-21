# -*- coding: utf-8 -*-
"""
LGS Soru Üretim Web Arayüzü V3
==============================
- Zorluk parametresi YOK
- Sadece Konu + Alt Konu
- V10 RAG entegrasyonu
- V10 Fine-tune modeli ile uyumlu
"""

from flask import Flask, render_template, request, jsonify
import json
import os
import sys
import re
import requests
import pickle
import numpy as np

# .env dosyasından API keylerini yükle
from dotenv import load_dotenv

# Yolları ayarla
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
env_path = os.path.join(project_dir, '.env')
load_dotenv(env_path)

app = Flask(__name__, template_folder='templates', static_folder='static')

# API Keys
COLAB_API_URL = os.getenv("COLAB_API_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Konu listesi - V10 ile uyumlu (zorluk YOK)
KONULAR = {
    "Paragraf": ["Ana Düşünce", "Başlık Bulma", "Anlatım Biçimi"],
    "Cümlede Anlam": ["Sebep-Sonuç", "Koşul", "Öznel-Nesnel", "Deyim"],
    "Yazım Kuralları": ["Noktalama", "Yazım Yanlışı"],
    "Dil Bilgisi": ["Fiilimsiler"],
    "Sözcükte Anlam": ["Çok Anlamlılık"],
}

# Smart RAG - Kılavuz tabanlı + Farkındalık konuları
from smart_rag import get_rag_context, FARKINDALIK_KONULARI

@app.route('/')
def index():
    api_configured = bool(COLAB_API_URL or GEMINI_API_KEY or GROQ_API_KEY)
    return render_template('index_v3.html', 
                          konular=KONULAR, 
                          farkindalik_konulari=FARKINDALIK_KONULARI,
                          api_configured=api_configured)

@app.route('/api/alt-konular/<konu>')
def get_alt_konular(konu):
    return jsonify(KONULAR.get(konu, ["Genel"]))

@app.route('/api/farkindalik-konulari')
def get_farkindalik_konulari():
    return jsonify(FARKINDALIK_KONULARI)

def build_prompt(konu, alt_konu, farkindalik=None):
    """Smart RAG destekli prompt oluşturur - kılavuz + farkındalık tabanlı."""
    
    # RAG context (farkındalık dahil)
    rag_context = get_rag_context(konu, alt_konu, farkindalik)
    
    prompt = f"""Konu: {konu}
Alt Konu: {alt_konu}

{rag_context}

---

Yukarıdaki kılavuza göre LGS Türkçe sorusu üret. SADECE JSON döndür.

ÇIKTI FORMATI:
{{"metin": "...", "soru": "...", "sik_a": "...", "sik_b": "...", "sik_c": "...", "sik_d": "...", "dogru_cevap": "A/B/C/D"}}"""
    
    return prompt

def repair_json(raw: str) -> str:
    """Bozuk JSON'u düzeltmeye çalışır - AGRESİF."""
    if not raw:
        return raw
    
    # 1. Tek tırnak → çift tırnak
    repaired = raw.replace("'", '"')
    
    # 2. Yanlış key isimlerini düzelt
    key_fixes = {
        '"metn"': '"metin"',
        '"sorusu"': '"soru"',
        '"soru_koku"': '"soru"',
        '"sik_A"': '"sik_a"',
        '"sik_B"': '"sik_b"',
        '"sik_C"': '"sik_c"',
        '"sik_D"': '"sik_d"',
        '"Sik_A"': '"sik_a"',
        '"Sik_B"': '"sik_b"',
        '"Sik_C"': '"sik_c"',
        '"Sik_D"': '"sik_d"',
        '"SIK_A"': '"sik_a"',
        '"SIK_B"': '"sik_b"',
        '"SIK_C"': '"sik_c"',
        '"SIK_D"': '"sik_d"',
        '"siki_A"': '"sik_a"',
        '"siki_B"': '"sik_b"',
        '"Siki_A"': '"sik_a"',
        '"Siki_B"': '"sik_b"',
        '"SIKi_C"': '"sik_c"',
        '"SiKD"': '"sik_d"',
        '"dogry cevp"': '"dogru_cevap"',
        '"dogru_cevap "': '"dogru_cevap"',
        '"cevap"': '"dogru_cevap"',
    }
    for wrong, correct in key_fixes.items():
        repaired = repaired.replace(wrong, correct)
    
    # 3. : " → ": " (boşluk düzeltme)
    repaired = re.sub(r'"\s*:\s*"', '": "', repaired)
    repaired = re.sub(r'"\s*:\s*\[', '": [', repaired)
    
    return repaired

def extract_content_regex(raw: str) -> dict:
    """JSON parse başarısız olursa regex ile içerik çıkar."""
    result = {"success": False}
    
    # Metin ara
    metin_match = re.search(r'"metin"\s*:\s*"([^"]+)"', raw)
    if not metin_match:
        metin_match = re.search(r'"metn"\s*:\s*"([^"]+)"', raw)
    if not metin_match:
        metin_match = re.search(r"'metin'\s*:\s*'([^']+)'", raw)
    
    # Soru ara
    soru_match = re.search(r'"soru"\s*:\s*"([^"]+)"', raw)
    if not soru_match:
        soru_match = re.search(r'"sorusu"\s*:\s*"([^"]+)"', raw)
    
    if metin_match and soru_match:
        result["metin"] = metin_match.group(1)
        result["soru"] = soru_match.group(1)
        result["sik_a"] = "Şık bulunamadı"
        result["sik_b"] = "Şık bulunamadı"
        result["sik_c"] = "Şık bulunamadı"
        result["sik_d"] = "Şık bulunamadı"
        result["dogru_cevap"] = "A"
        result["success"] = True
        print("   ⚠️ Regex fallback kullanıldı")
    
    return result

def call_api(prompt):
    """Colab API'yi çağırır."""
    if not COLAB_API_URL:
        return {"error": "Colab URL yok"}
    
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        url = f"{COLAB_API_URL.rstrip('/')}/generate"
        payload = {"prompt": {"user": prompt}}
        
        response = requests.post(url, json=payload, timeout=120, verify=False)
        data = response.json()
        
        raw = data.get("result", data.get("response", ""))
        
        # JSON REPAIR uygula
        repaired = repair_json(raw)
        
        # DEBUG: API yanıtını göster
        print(f"🔍 API RAW YANIT (ilk 500):")
        print(raw[:500] if raw else "BOŞ YANIT")
        print("-" * 50)
        
        return {"raw": repaired}  # Repaired version döndür
    except Exception as e:
        print(f"❌ API HATA: {e}")
        return {"error": str(e)}

def parse_response(raw):
    """JSON çıktıyı parse eder - ESNEK (farklı key formatlarını kabul eder)."""
    result = {"success": False}
    
    if not raw:
        return result
    
    try:
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1:
            data = json.loads(raw[start:end+1])
            
            # ESNEK KEY MAPPING - Model farklı formatlar üretebilir
            result["metin"] = (
                data.get("metin") or data.get("metn") or 
                data.get("text") or data.get("paragraf") or ""
            )
            result["soru"] = (
                data.get("soru") or data.get("sorusu") or 
                data.get("soru_koku") or data.get("question") or ""
            )
            
            # Şıklar için esnek arama
            def get_option(data, letter):
                variants = [
                    f"sik_{letter.lower()}", f"sik{letter.lower()}", 
                    f"siki_{letter}", f"sicib_{letter}", f"cikci_{letter}", f"dikti_{letter}",
                    f"şık_{letter.lower()}", f"option_{letter.lower()}",
                    letter.upper(), letter.lower()
                ]
                for v in variants:
                    if data.get(v):
                        return data.get(v)
                return ""
            
            result["sik_a"] = get_option(data, "a")
            result["sik_b"] = get_option(data, "b")
            result["sik_c"] = get_option(data, "c")
            result["sik_d"] = get_option(data, "d")
            
            # Doğru cevap
            dc = (
                data.get("dogru_cevap") or data.get("cevap") or 
                data.get("dogru") or data.get("answer") or ""
            )
            result["dogru_cevap"] = dc.upper().strip()[-1] if dc else ""
            
            # Validasyon - en az metin ve soru varsa başarılı say
            if result["metin"] and result["soru"]:
                # Şıklar eksikse data'dan ilk 4 key'i dene
                if not all([result["sik_a"], result["sik_b"], result["sik_c"], result["sik_d"]]):
                    keys = [k for k in data.keys() if k not in ["metin", "metn", "soru", "sorusu", "dogru_cevap", "cevap"]]
                    for i, letter in enumerate(["sik_a", "sik_b", "sik_c", "sik_d"]):
                        if not result[letter] and i < len(keys):
                            result[letter] = str(data.get(keys[i], ""))
                
                if result["dogru_cevap"] in ["A", "B", "C", "D"]:
                    result["success"] = True
                elif result["sik_a"] and result["sik_b"]:
                    # Doğru cevap yoksa A olarak varsay
                    result["dogru_cevap"] = "A"
                    result["success"] = True
                    
    except Exception as e:
        print(f"   Parse Exception: {e}")
        # JSON parse başarısız - regex fallback dene
        result = extract_content_regex(raw)
    
    return result

@app.route('/api/generate', methods=['POST'])
def generate():
    """Soru üretir - V3 Smart RAG akışı + Farkındalık."""
    data = request.json
    
    konu = data.get('konu', 'Paragraf')
    alt_konu = data.get('alt_konu', 'Ana Düşünce')
    farkindalik = data.get('farkindalik', None)  # Yeni: Farkındalık konusu
    
    # Smart RAG ile prompt oluştur (kılavuz + farkındalık tabanlı)
    prompt = build_prompt(konu, alt_konu, farkindalik)
    
    if farkindalik:
        print(f"📝 Smart RAG prompt: {len(prompt)} karakter, Alt Konu: {alt_konu}, Farkındalık: {farkindalik}")
    else:
        print(f"📝 Smart RAG prompt: {len(prompt)} karakter, Alt Konu: {alt_konu}")
    
    # API kontrolü
    if not COLAB_API_URL:
        return jsonify({
            'success': True,
            'mode': 'prompt',
            'prompt': prompt,
            'konu': konu,
            'alt_konu': alt_konu,
            'farkindalik': farkindalik,
            'message': 'Colab API yok - Prompt modunda'
        })
    
    # Retry
    max_retries = 3
    for attempt in range(max_retries):
        print(f"🔄 Deneme {attempt + 1}/{max_retries}")
        
        response = call_api(prompt)
        if "error" in response:
            print(f"   ⚠ API hatası: {response['error']}")
            continue
        
        result = parse_response(response.get("raw", ""))
        if result["success"]:
            print("   ✅ Başarılı!")
            return jsonify({
                'success': True,
                'mode': 'generated',
                'konu': konu,
                'alt_konu': alt_konu,
                'question': {
                    'metin': result['metin'],
                    'soru_koku': result['soru'],
                    'sik_a': result['sik_a'],
                    'sik_b': result['sik_b'],
                    'sik_c': result['sik_c'],
                    'sik_d': result['sik_d'],
                    'dogru_cevap': result['dogru_cevap']
                }
            })
        else:
            print("   ⚠ Parse başarısız")
    
    # Başarısız
    return jsonify({
        'success': True,
        'mode': 'prompt',
        'prompt': prompt,
        'konu': konu,
        'alt_konu': alt_konu,
        'message': 'Soru üretilemedi - Prompt modunda'
    })

if __name__ == '__main__':
    print("🚀 LGS Soru Üretim Web Arayüzü V3 başlatılıyor...")
    print("📍 http://localhost:5000")
    print("📝 Format: Konu + Alt Konu (zorluk YOK)")
    
    if COLAB_API_URL:
        print(f"✅ Colab API: {COLAB_API_URL[:50]}...")
    else:
        print("⚠ Colab API yok - Prompt modunda")
    
    app.run(debug=True, port=5000)
