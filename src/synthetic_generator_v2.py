# -*- coding: utf-8 -*-
"""
PROFESYONEL SENTETİK VERİ ÜRETİCİSİ v2
======================================
RAG V3 Entegreli, Dengeli Dağılımlı, Kalite Validasyonlu
"""

import json
import re
import time
import os
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv
import requests

# Load environment
script_dir = Path(__file__).parent
project_dir = script_dir.parent
load_dotenv(project_dir / ".env")

# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# RAG V3 Kuralları (hardcoded for reliability)
QUESTION_TYPE_SPECS = {
    "Paragraf_Ana Düşünce": {
        "min_words": 120, "max_words": 220,
        "numbered": False,
        "highlights": False,
        "description": "Metnin ana fikri, temel mesajı"
    },
    "Paragraf_Başlık Bulma": {
        "min_words": 120, "max_words": 220,
        "numbered": False,
        "highlights": False,
        "description": "Metne uygun başlık bulma"
    },
    "Paragraf_Anlatım Biçimi": {
        "min_words": 120, "max_words": 220,
        "numbered": False,
        "highlights": False,
        "description": "Anlatım türü (öyküleme, betimleme, açıklama, tartışma)"
    },
    "Cümlede Anlam_Sebep-Sonuç": {
        "min_words": 80, "max_words": 150,
        "numbered": False,
        "highlights": False,
        "description": "Neden-sonuç ilişkisi"
    },
    "Cümlede Anlam_Koşul": {
        "min_words": 80, "max_words": 150,
        "numbered": False,
        "highlights": False,
        "description": "Koşul anlamı (-sa/-se, eğer)"
    },
    "Cümlede Anlam_Öznel-Nesnel": {
        "min_words": 80, "max_words": 150,
        "numbered": False,
        "highlights": False,
        "description": "Öznel (kişisel) vs Nesnel (kanıtlanabilir) yargı"
    },
    "Cümlede Anlam_Deyim": {
        "min_words": 80, "max_words": 150,
        "numbered": False,
        "highlights": False,
        "description": "Deyimlerin anlamı"
    },
    "Sözcükte Anlam_Çok Anlamlılık": {
        "min_words": 40, "max_words": 80,
        "numbered": True,  # Numaralı cümleler
        "highlights": True,  # Hedef kelime vurgusu
        "description": "Bir kelimenin farklı anlamları"
    },
    "Sözcükte Anlam_Eş Anlamlılık": {
        "min_words": 40, "max_words": 80,
        "numbered": True,
        "highlights": True,
        "description": "Eş anlamlı kelimeler"
    },
    "Sözcükte Anlam_Zıt Anlamlılık": {
        "min_words": 40, "max_words": 80,
        "numbered": True,
        "highlights": True,
        "description": "Zıt anlamlı kelimeler"
    },
    "Dil Bilgisi_Fiilimsiler": {
        "min_words": 100, "max_words": 180,
        "numbered": False,
        "highlights": False,
        "description": "İsim-fiil, sıfat-fiil, zarf-fiil"
    },
    "Dil Bilgisi_Kelime Türleri": {
        "min_words": 100, "max_words": 180,
        "numbered": False,
        "highlights": False,
        "description": "İsim, fiil, sıfat, zarf, zamir vb."
    },
    "Yazım Kuralları_Noktalama": {
        "min_words": 80, "max_words": 150,
        "numbered": False,
        "highlights": False,
        "description": "Noktalama işaretleri"
    },
    "Yazım Kuralları_Yazım Yanlışı": {
        "min_words": 80, "max_words": 150,
        "numbered": False,
        "highlights": False,
        "description": "Yazım hataları"
    },
}

TEMALAR = [
    "Teknoloji", "Çevre", "Sağlık", "Eğitim", "Spor", 
    "Sanat", "Bilim", "Tarih", "Edebiyat", "Müzik",
    "Doğa", "Hayvanlar", "Uzay", "İletişim", "Aile"
]

def count_words(text):
    """Kelime sayısını hesapla."""
    return len(re.findall(r'\b\w+\b', text or "", re.UNICODE))

def call_groq_api(prompt, max_retries=3):
    """Groq API çağrısı with retry."""
    for attempt in range(max_retries):
        try:
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.85,  # Diversity için yüksek
                "max_tokens": 1500,
            }
            
            response = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 10
                print(f"   ⏳ Rate limit, {wait_time}sn bekleniyor...")
                time.sleep(wait_time)
                continue
            else:
                print(f"   ❌ API Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"   ❌ Exception: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return None
    
    return None

def build_professional_prompt(konu, alt_konu, tema, spec):
    """
    PROFESYONEL PROMPT - RAG V3 Stratejileri Dahil
    
    Multi-shot learning + explicit rules + quality emphasis
    """
    
    min_w = spec["min_words"]
    max_w = spec["max_words"]
    numbered = spec["numbered"]
    highlights = spec["highlights"]
    desc = spec["description"]
    
    prompt = f"""Sen MEB LGS 8. sınıf Türkçe sınavları için PROFESYONEL soru hazırlayan bir uzman yazarsın.

## GÖREV
Konu: {konu}
Alt Konu: {alt_konu} ({desc})
Tema: {tema}

## KESİN KURALLAR (UYMAYANLAR REDDEDİLİR!)

### 1. Metin Yapısı
- Kelime sayısı: TAM OLARAK {min_w}-{max_w} kelime arası
- Format: {"NUMARALI cümleler (I. II. III. IV.)" if numbered else "PARAGRAF (numaralı cümle KULLANMA)"}
{"- Hedef kelime: Tırnak içinde vurgula (örn: 'göz')" if highlights else ""}
- SADECE TÜRKÇE! Çince, İngilizce, Arapça YASAK!

### 2. Metin Kalitesi
- LGS seviyesine uygun ✅
- Akıcı ve doğal dil ✅
- Gramere uygun ✅
- İçerik temaya uygun ✅
{"- KELİME SAYISI ÇOK ÖNEMLİ: " + str(min_w) + "-" + str(max_w) + " arası olmalı!" if True else ""}

### 3. Soru Kalitesi
- Metinle doğrudan ilgili ✅
- Tek doğru cevap ✅
- 4 şık (A, B, C, D) ✅
- Çeldiriciler mantıklı ama yanlış ✅
- Doğru cevap metinde açıkça var ✅

## ÇELDİRİCİ TAKTİKLERİ

**Etkili çeldiriciler:**
1. Metinde geçen ama soruyla ilgisiz bilgi
2. Doğruya yakın ama eksik/fazla bilgi  
3. Başka bağlamda doğru olabilecek bilgi
4. Yaygın yanılgılar

**Kaçınılacaklar:**
- Saçma, alakasız şıklar ❌
- Çok kolay eleme ❌
- Metinde hiç geçmeyen kavramlar ❌

## ÇIKTI FORMATI

SADECE bu JSON formatında döndür (başka hiçbir şey yazma):

{{"metin": "Metin buraya ({min_w}-{max_w} kelime)", "soru": "Soru metni", "sik_a": "A şıkkı", "sik_b": "B şıkkı", "sik_c": "C şıkkı", "sik_d": "D şıkkı", "dogru_cevap": "A"}}

## ÖNEMLİ HATIRLATMALAR

1. Metin {min_w}-{max_w} kelime OLMALIDIR (daha az veya fazla KABUL EDİLMEZ)
2. SADECE JSON döndür (açıklama, yorum YOK)
3. SADECE TÜRKÇE (başka dil YOK)
4. LGS standartlarına UYGUN olmalı

ŞİMDİ BAŞLA - SADECE JSON DÖNDÜR!"""
    
    return prompt

def validate_question(data_obj, spec):
    """
    Sıkı kalite kontrolü
    
    Returns: (is_valid, reason, word_count)
    """
    
    # Required fields check
    required = ["metin", "soru", "sik_a", "sik_b", "sik_c", "sik_d", "dogru_cevap"]
    for field in required:
        if field not in data_obj or not data_obj[field]:
            return False, f"Missing: {field}", 0
    
    metin = data_obj["metin"]
    soru = data_obj["soru"]
    
    # Word count check (STRICT)
    wc = count_words(metin)
    min_w = spec["min_words"]
    max_w = spec["max_words"]
    
    # ±10% tolerance (çok strict olmasın)
    tolerance = 0.1
    min_tolerant = int(min_w * (1 - tolerance))
    max_tolerant = int(max_w * (1 + tolerance))
    
    if wc < min_tolerant:
        return False, f"Too short: {wc} < {min_tolerant}", wc
    if wc > max_tolerant:
        return False, f"Too long: {wc} > {max_tolerant}", wc
    
    # Format check (numbered vs paragraph)
    has_numbered = bool(re.search(r'\b[IVX]+\.\s', metin))
    if spec["numbered"] and not has_numbered:
        return False, "Numaralı cümle yok", wc
    if not spec["numbered"] and has_numbered:
        return False, "Numaralı cümle olmamalı", wc
    
    # Language check (no Chinese/Arabic/etc)
    has_chinese = any(0x4E00 <= ord(c) <= 0x9FFF for c in metin + soru)
    has_arabic = any(0x0600 <= ord(c) <= 0x06FF for c in metin + soru)
    
    if has_chinese or has_arabic:
        return False, "Foreign language detected", wc
    
    # Doğru cevap check
    if data_obj["dogru_cevap"] not in ["A", "B", "C", "D"]:
        return False, "Invalid dogru_cevap", wc
    
    return True, "OK", wc

def generate_balanced_dataset(
    existing_data_path, 
    output_path, 
    target_per_type=30,
    max_retries_per_question=3
):
    """
    Dengeli sentetik veri üret.
    
    Args:
        existing_data_path: Mevcut veri (dağılım analizi için)
        output_path: Çıktı dosyası
        target_per_type: Her soru tipi için hedef sayı
        max_retries_per_question: Her soru için max deneme
    """
    
    # Mevcut dağılımı analiz et
    existing_counts = Counter()
    
    if Path(existing_data_path).exists():
        with open(existing_data_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    ex = json.loads(line.strip())
                    user = ex.get("user", "")
                    if "Konu:" in user and "Alt Konu:" in user:
                        konu = user.split("Konu:")[1].split("\n")[0].strip()
                        alt_konu = user.split("Alt Konu:")[1].split("\n")[0].strip()
                        key = f"{konu}_{alt_konu}"
                        existing_counts[key] += 1
                except:
                    pass
    
    print(f"\n{'='*70}")
    print(f"PROFESYONEL SENTETİK VERİ ÜRETİCİSİ v2")
    print(f"{'='*70}")
    print(f"Mevcut veri: {existing_data_path}")
    print(f"Çıktı: {output_path}")
    print(f"Hedef: Her soru tipi için {target_per_type} örnek")
    print(f"{'='*70}\n")
    
    # Üretim planı
    generation_plan = {}
    
    for question_type, spec in QUESTION_TYPE_SPECS.items():
        current_count = existing_counts.get(question_type, 0)
        need = max(0, target_per_type - current_count)
        
        if need > 0:
            generation_plan[question_type] = need
            print(f"📝 {question_type:40s}: Mevcut={current_count:3d}, Hedef={target_per_type:3d}, Üretilecek={need:3d}")
    
    if not generation_plan:
        print("\n✅ Tüm soru tipleri hedef sayıda! Üretim gerekmiyor.")
        return
    
    total_to_generate = sum(generation_plan.values())
    print(f"\n{'='*70}")
    print(f"TOPLAM ÜRETİLECEK: {total_to_generate} örnek")
    print(f"{'='*70}\n")
    
    # Üretim başlasın
    generated = []
    total_success = 0
    total_attempts = 0
    
    for question_type, count_needed in generation_plan.items():
        konu, alt_konu = question_type.split("_", 1)
        spec = QUESTION_TYPE_SPECS[question_type]
        
        print(f"\n{'='*70}")
        print(f"Üretiliyor: {question_type}")
        print(f"{'='*70}")
        
        success_count = 0
        attempts = 0
        
        while success_count < count_needed and attempts < count_needed * max_retries_per_question:
            attempts += 1
            total_attempts += 1
            
            # Random tema
            import random
            tema = random.choice(TEMALAR)
            
            # Prompt oluştur
            prompt = build_professional_prompt(konu, alt_konu, tema, spec)
            
            # API çağrısı
            response = call_groq_api(prompt)
            
            if not response:
                print(f"   ❌ API failed (attempt {attempts})")
                continue
            
            # JSON parse
            try:
                start = response.find('{')
                end = response.rfind('}')
                if start == -1 or end == -1:
                    print(f"   ❌ No JSON found (attempt {attempts})")
                    continue
                
                data_obj = json.loads(response[start:end+1])
                
                # Validate
                is_valid, reason, wc = validate_question(data_obj, spec)
                
                if not is_valid:
                    print(f"   ❌ Validation failed: {reason} (attempt {attempts})")
                    continue
                
                # Success!
                success_count += 1
                total_success += 1
                
                # Save format
                generated.append({
                    "user": f"Konu: {konu}\\nAlt Konu: {alt_konu}\\n\\nBu kriterlere göre LGS Türkçe sorusu üret.",
                    "assistant": json.dumps(data_obj, ensure_ascii=False)
                })
                
                print(f"   ✅ Success {success_count}/{count_needed} | WC: {wc} | Attempt: {attempts}")
                
                # Rate limit koruması
                time.sleep(1)
                
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON parse error: {str(e)} (attempt {attempts})")
                continue
            except Exception as e:
                print(f"   ❌ Unexpected error: {str(e)} (attempt {attempts})")
                continue
        
        print(f"\\n  📊 {question_type}: {success_count}/{count_needed} başarılı ({attempts} deneme)")
    
    # Kaydet
    print(f"\\n{'='*70}")
    print(f"KAYIT EDİLİYOR...")
    print(f"{'='*70}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for example in generated:
            f.write(json.dumps(example, ensure_ascii=False) + '\\n')
    
    print(f"\\n✅ {len(generated)} örnek kaydedildi: {output_path}")
    print(f"\\n{'='*70}")
    print(f"ÖZET:")
    print(f"{'='*70}")
    print(f"Toplam deneme:  {total_attempts}")
    print(f"Başarılı:       {total_success} ({100*total_success/total_attempts:.1f}%)")
    print(f"Başarısız:      {total_attempts - total_success}")
    print(f"{'='*70}")

if __name__ == "__main__":
    # Paths
    existing_train = project_dir / "data" / "v12_quality_filtered" / "train.jsonl"
    output_synthetic = project_dir / "data" / "synthetic_v2" / "train_synthetic.jsonl"
    
    output_synthetic.parent.mkdir(exist_ok=True)
    
    # Üret
    generate_balanced_dataset(
        existing_data_path=existing_train,
        output_path=output_synthetic,
        target_per_type=30,  # Her soru tipi için 30 örnek
        max_retries_per_question=5  # Max 5 deneme per soru
    )
