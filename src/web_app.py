# -*- coding: utf-8 -*-
"""
LGS Soru Üretim Web Arayüzü - Few-shot RAG + Kalite Kontrolü
=============================================================
"""

from flask import Flask, render_template, request, jsonify
import json
import os
import sys

# .env dosyasından API keylerini yükle
from dotenv import load_dotenv

# .env yolunu belirle
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
env_path = os.path.join(project_dir, '.env')
load_dotenv(env_path)

# src modüllerini import için
sys.path.insert(0, script_dir)

from question_generator import LGSQuestionGenerator, parse_llm_response, validate_question
from api_client import QuestionGeneratorAPI
# from local_inference import get_model  # Yerel model devre dışı

app = Flask(__name__, template_folder='templates', static_folder='static')

# Global instances
generator = None
question_api = None

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Konu listesi - V8 Eğitim verisiyle %100 uyumlu
KONULAR = {
    "Paragraf": ["Ana Düşünce", "Başlık Bulma", "Anlatım Biçimi"],
    "Cümlede Anlam": ["Sebep-Sonuç", "Koşul", "Öznel-Nesnel", "Deyim"],
    "Yazım Kuralları": ["Noktalama", "Yazım Yanlışı"],
    "Dil Bilgisi": ["Fiilimsiler"],
    "Sözcükte Anlam": ["Çok Anlamlılık"],
}



def init_services():
    """Servisleri başlatır."""
    global generator, question_api
    
    if generator is None:
        data_path = os.path.join(project_dir, "data", "guncel_yapilandirilmiş_veri_seti_v3_clean.json")
        generator = LGSQuestionGenerator(data_path)
        generator.initialize()
    
    if question_api is None:
        question_api = QuestionGeneratorAPI(GEMINI_API_KEY, GROQ_API_KEY)


@app.route('/')
def index():
    COLAB_API_URL = os.getenv("COLAB_API_URL", "")
    api_configured = bool(GEMINI_API_KEY or GROQ_API_KEY or COLAB_API_URL)
    return render_template('index.html', konular=KONULAR, api_configured=api_configured)


@app.route('/api/alt-konular/<konu>')
def get_alt_konular(konu):
    return jsonify(KONULAR.get(konu, ["Genel"]))


@app.route('/api/generate', methods=['POST'])
def generate():
    """Soru üretir - Few-shot RAG + Kalite Kontrolü + Retry."""
    data = request.json
    
    konu = data.get('konu', 'Paragraf')
    alt_konu = data.get('alt_konu', 'Ana Düşünce')
    zorluk = data.get('zorluk', 'orta')
    
    init_services()
    
    # Few-shot prompt oluştur
    prompt_data = generator.generate_prompt(konu, alt_konu, zorluk)
    prompt = prompt_data['prompt']
    
    # UI için prompt'u string'e çevir
    prompt_str = prompt
    if isinstance(prompt, dict):
        prompt_str = f"SYSTEM: {prompt.get('system', '')}\n\nUSER: {prompt.get('user', '')}"

    # API kontrolü (Colab URL'i de kontrol et)
    COLAB_API_URL = os.getenv("COLAB_API_URL", "")
    if not (GEMINI_API_KEY or GROQ_API_KEY or COLAB_API_URL):
        return jsonify({
            'success': True,
            'mode': 'prompt',
            'prompt': prompt_str,
            'konu': konu,
            'alt_konu': alt_konu,
            'zorluk': zorluk,
            'farkindalik_konusu': prompt_data.get('farkindalik_konusu'),
            'example_count': prompt_data.get('example_count', 0),
            'message': 'API key veya Colab URL yok - Prompt modunda'
        })
    
    # Retry mekanizması ile soru üret
    max_retries = 3
    best_result = None
    best_score = 0
    best_validation_score = 0
    
    for attempt in range(max_retries):
        print(f"🔄 Soru üretme denemesi {attempt + 1}/{max_retries}")
        
        # API çağrısı
        response = question_api.generate_question(prompt)
        
        if "error" in response:
            print(f"⚠️ API hatası: {response.get('error')}")
            continue
        
        # Parse et
        parsed = parse_llm_response(response.get("raw", ""))
        
        if not parsed["success"]:
            print("⚠️ Parse başarısız")
            continue
        
        # Kalite kontrolü 1: Template quality
        quality = validate_question(parsed)
        print(f"📊 Template kalite skoru: {quality['score']}/100")
        
        # Kalite kontrolü 2: Topic matching validation
        from question_validator import validate_question as topic_validate
        topic_validation = topic_validate(parsed, alt_konu, parsed.get('metin', ''))
        print(f"🎯 Konu uyumu skoru: {topic_validation['score']}/100")
        
        # Hataları ve uyarıları logla
        if not topic_validation['valid']:
            for issue in topic_validation['issues']:
                print(f"   {issue}")
        for warning in topic_validation['warnings']:
            print(f"   {warning}")
        
        # Toplam skor: İki skor ortalaması
        combined_score = (quality['score'] + topic_validation['score']) / 2
        
        if quality["ok"] and topic_validation["valid"] and combined_score > best_score:
            best_result = parsed
            best_score = combined_score
            best_validation_score = topic_validation["score"]
            
            # Yeterince iyi ise dur
            if combined_score >= 75:  # 85'ten 75'e düşürdük
                print(f"✅ Yüksek kaliteli soru üretildi! (Toplam: {combined_score:.0f}/100)")
                break
    
    
    # Sonuç döndür
    if best_result:
        return jsonify({
            'success': True,
            'mode': 'generated',
            'konu': konu,
            'alt_konu': alt_konu,
            'zorluk': zorluk,
            'farkindalik_konusu': prompt_data.get('farkindalik_konusu'),
            'example_count': prompt_data.get('example_count', 0),
            'quality_score': best_score,
            'question': {
                'metin': best_result.get('metin', ''),
                'soru_koku': best_result.get('soru_koku', ''),
                'sik_a': best_result.get('sik_a', ''),
                'sik_b': best_result.get('sik_b', ''),
                'sik_c': best_result.get('sik_c', ''),
                'sik_d': best_result.get('sik_d', ''),
                'dogru_cevap': best_result.get('dogru_cevap', '')
            }
        })
    else:
        # Başarısız - prompt döndür
        return jsonify({
            'success': True,
            'mode': 'prompt',
            'prompt': prompt_str,
            'konu': konu,
            'alt_konu': alt_konu,
            'zorluk': zorluk,
            'farkindalik_konusu': prompt_data.get('farkindalik_konusu'),
            'example_count': prompt_data.get('example_count', 0),
            'message': 'Kaliteli soru üretilemedi, prompt\'u manuel kullanın'
        })


if __name__ == '__main__':
    print("🚀 LGS Soru Üretim Web Arayüzü başlatılıyor...")
    print("📍 http://localhost:5000")
    
    if GEMINI_API_KEY or GROQ_API_KEY:
        print("✅ API key bulundu - Few-shot RAG + Kalite Kontrolü aktif")
    else:
        print("⚠️  API key bulunamadı - Prompt modunda")
    
    app.run(debug=True, port=5000)
