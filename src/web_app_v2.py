# -*- coding: utf-8 -*-
"""
LGS Soru Üretim Web Arayüzü V2 - SADELEŞTİRİLMİŞ
================================================
- Şablon sistemi bypass
- Doğrudan basit prompt
- RAG V2 ile 1818 soru
"""

from flask import Flask, render_template, request, jsonify
import json
import os
import sys
import re
import requests

# .env dosyasından API keylerini yükle
from dotenv import load_dotenv

# Yolları ayarla
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
env_path = os.path.join(project_dir, '.env')
load_dotenv(env_path)

# RAG V2 import
sys.path.insert(0, script_dir)
from rag_v2 import initialize_rag, get_rag

app = Flask(__name__, template_folder='templates', static_folder='static')

# API Keys
COLAB_API_URL = os.getenv("COLAB_API_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Konu listesi - V8 Eğitim verisiyle %100 uyumlu (sadece güçlü alt konular)
KONULAR = {
    "Paragraf": ["Ana Düşünce", "Başlık Bulma", "Anlatım Biçimi"],
    "Cümlede Anlam": ["Sebep-Sonuç", "Koşul", "Öznel-Nesnel", "Deyim"],
    "Yazım Kuralları": ["Noktalama", "Yazım Yanlışı"],
    "Dil Bilgisi": ["Fiilimsiler"],
    "Sözcükte Anlam": ["Çok Anlamlılık"],
}

# RAG başlat
rag = None
def init_rag():
    global rag
    if rag is None:
        data_path = os.path.join(project_dir, "data", "lgs_finetune_data_v8_full_rag.jsonl")
        if os.path.exists(data_path):
            rag = initialize_rag(data_path)
        else:
            print(f"⚠ RAG veri dosyası bulunamadı: {data_path}")


@app.route('/')
def index():
    api_configured = bool(COLAB_API_URL or GEMINI_API_KEY or GROQ_API_KEY)
    return render_template('index.html', konular=KONULAR, api_configured=api_configured)


@app.route('/api/alt-konular/<konu>')
def get_alt_konular(konu):
    return jsonify(KONULAR.get(konu, ["Genel"]))


def build_simple_prompt(konu: str, alt_konu: str, zorluk: str, rag_refs: str = "") -> str:
    """Basit ve temiz prompt oluşturur."""
    
    # Alt konu bazlı soru kökü önerileri
    soru_koku_onerileri = {
        "Ana Düşünce": "Bu parçanın ana düşüncesi aşağıdakilerden hangisidir?",
        "Başlık Bulma": "Bu metne en uygun başlık aşağıdakilerden hangisidir?",
        "Anlatım Biçimi": "Bu parçanın anlatım biçimi aşağıdakilerden hangisidir?",
        "Sebep-Sonuç": "Bu parçada belirtilen durumun NEDENİ aşağıdakilerden hangisidir?",
        "Koşul": "Bu cümlede koşul anlamı hangi sözcükle sağlanmıştır?",
        "Öznel-Nesnel": "Aşağıdaki cümlelerin hangisi öznel yargı içermektedir?",
        "Deyim": "Bu parçadaki altı çizili deyimin anlamı aşağıdakilerden hangisidir?",
        "Noktalama": "Bu parçada virgülün kullanım amacı aşağıdakilerden hangisidir?",
        "Yazım Yanlışı": "Aşağıdaki cümlelerin hangisinde yazım yanlışı vardır?",
        "Fiilimsiler": "Bu parçadaki altı çizili sözcüklerden hangisi fiilimsidir?",
        "Çok Anlamlılık": "Altı çizili sözcük aşağıdaki cümlelerin hangisinde farklı anlamda kullanılmıştır?",
    }
    
    # Zorluk talimatları
    zorluk_talimati = {
        "kolay": "Metin açık olsun. Doğru cevap kolayca anlaşılsın.",
        "orta": "Metin dikkatli okunmalı. Doğru cevap çıkarım gerektirsin.",
        "zor": "Şıklar birbirine yakın olsun. NEGATİF kök kullan (ulaşılamaz, söylenemez)."
    }
    
    soru_koku = soru_koku_onerileri.get(alt_konu, "Bu parçayla ilgili aşağıdakilerden hangisi doğrudur?")
    zorluk_talimat = zorluk_talimati.get(zorluk.lower(), zorluk_talimati["orta"])
    
    prompt = f"""Konu: {konu}
Alt Konu: {alt_konu}
Zorluk: {zorluk}

GÖREV: {alt_konu} konusunda LGS Türkçe sorusu üret.

KURALLAR:
1. MUTLAKA "{alt_konu}" konusuna uygun soru sor
2. Soru kökü önerisi: "{soru_koku}"
3. {zorluk_talimat}
4. Numaralanmış cümle formatı KULLANMA
5. 4 şık (A, B, C, D) dengeli uzunlukta olsun
6. JSON formatında cevap ver

{rag_refs}

ÇIKTI FORMATI:
{{"metin": "...", "soru": "...", "sik_a": "...", "sik_b": "...", "sik_c": "...", "sik_d": "...", "dogru_cevap": "A/B/C/D"}}"""
    
    return prompt


def call_colab_api(prompt: str) -> dict:
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
        
        # Colab API 'result' döndürür, eski API 'response' döndürür
        raw = data.get("result", data.get("response", ""))
        print(f"🔍 API RAW: {raw[:300]}...")  # DEBUG
        return {"raw": raw}
    except Exception as e:
        print(f"❌ API HATA: {e}")
        return {"error": str(e)}


def parse_response(raw: str) -> dict:
    """JSON çıktıyı parse eder."""
    result = {
        "metin": "",
        "soru": "",
        "sik_a": "",
        "sik_b": "",
        "sik_c": "",
        "sik_d": "",
        "dogru_cevap": "",
        "success": False
    }
    
    if not raw:
        return result
    
    try:
        # JSON bul ve parse et
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1:
            json_str = raw[start:end+1]
            data = json.loads(json_str)
            
            result["metin"] = data.get("metin", "")
            result["soru"] = data.get("soru", "")
            result["sik_a"] = data.get("sik_a", "")
            result["sik_b"] = data.get("sik_b", "")
            result["sik_c"] = data.get("sik_c", "")
            result["sik_d"] = data.get("sik_d", "")
            result["dogru_cevap"] = data.get("dogru_cevap", "").upper()
            
            # Başarı kontrolü
            if all([result["metin"], result["soru"], result["sik_a"], 
                    result["sik_b"], result["sik_c"], result["sik_d"],
                    result["dogru_cevap"] in ["A", "B", "C", "D"]]):
                result["success"] = True
    except:
        pass
    
    return result


def simple_validate(result: dict, alt_konu: str) -> bool:
    """Basit doğrulama - sadece kritik kontroller."""
    if not result["success"]:
        return False
    
    soru = result["soru"].lower()
    
    # Numaralanmış cümle kontrolü (metinde numara yoksa)
    if "numaralanmış" in soru:
        metin = result["metin"]
        if not any(p in metin for p in ["(I)", "(II)", "I.", "II.", "1.", "2."]):
            print("   ⚠ Numaralanmış format ama metinde numara yok")
            return False
    
    # Boş şık kontrolü
    for sik in [result["sik_a"], result["sik_b"], result["sik_c"], result["sik_d"]]:
        if len(sik.strip()) < 3:
            print("   ⚠ Çok kısa şık var")
            return False
    
    return True


@app.route('/api/generate', methods=['POST'])
def generate():
    """Soru üretir - SADELEŞTİRİLMİŞ AKIŞ."""
    data = request.json
    
    konu = data.get('konu', 'Paragraf')
    alt_konu = data.get('alt_konu', 'Ana Düşünce')
    zorluk = data.get('zorluk', 'orta')
    
    # RAG başlat
    init_rag()
    
    # RAG referansları al
    rag_refs = ""
    if rag:
        rag_refs = rag.get_reference_text(konu, alt_konu, zorluk)
        if rag_refs:
            print(f"🔗 RAG referansları eklendi")
    
    # Basit prompt oluştur
    prompt = build_simple_prompt(konu, alt_konu, zorluk, rag_refs)
    
    # API kontrolü
    if not COLAB_API_URL:
        return jsonify({
            'success': True,
            'mode': 'prompt',
            'prompt': prompt,
            'konu': konu,
            'alt_konu': alt_konu,
            'zorluk': zorluk,
            'message': 'Colab API URL yok - Prompt modunda'
        })
    
    # Retry mekanizması
    max_retries = 3
    best_result = None
    
    for attempt in range(max_retries):
        print(f"🔄 Deneme {attempt + 1}/{max_retries}")
        
        # API çağrısı
        response = call_colab_api(prompt)
        
        if "error" in response:
            print(f"   ⚠ API hatası: {response['error']}")
            continue
        
        # Parse et
        result = parse_response(response.get("raw", ""))
        
        if not result["success"]:
            print("   ⚠ Parse başarısız")
            continue
        
        # Doğrula
        if simple_validate(result, alt_konu):
            best_result = result
            print("   ✅ Başarılı!")
            break
        else:
            # İlk geçerli sonucu sakla (validation geçemese bile)
            if best_result is None:
                best_result = result
    
    # Sonuç döndür
    if best_result and best_result["success"]:
        return jsonify({
            'success': True,
            'mode': 'generated',
            'konu': konu,
            'alt_konu': alt_konu,
            'zorluk': zorluk,
            'question': {
                'metin': best_result['metin'],
                'soru_koku': best_result['soru'],
                'sik_a': best_result['sik_a'],
                'sik_b': best_result['sik_b'],
                'sik_c': best_result['sik_c'],
                'sik_d': best_result['sik_d'],
                'dogru_cevap': best_result['dogru_cevap']
            }
        })
    else:
        return jsonify({
            'success': True,
            'mode': 'prompt',
            'prompt': prompt,
            'konu': konu,
            'alt_konu': alt_konu,
            'zorluk': zorluk,
            'message': 'Soru üretilemedi - Prompt modunda'
        })


if __name__ == '__main__':
    print("🚀 LGS Soru Üretim Web Arayüzü V2 başlatılıyor...")
    print("📍 http://localhost:5000")
    
    if COLAB_API_URL:
        print(f"✅ Colab API: {COLAB_API_URL[:50]}...")
    else:
        print("⚠ Colab API URL yok - Prompt modunda")
    
    app.run(debug=True, port=5000)
