# -*- coding: utf-8 -*-
"""
DATA QUALITY FILTER - Strict Word Count
========================================
Sadece ideal kelime aralığındaki örnekleri tut.
"""

import json
import re
from pathlib import Path
from collections import Counter

def count_words(text):
    """Kelime sayısını hesapla."""
    return len(re.findall(r'\b\w+\b', text or "", re.UNICODE))

def get_word_count_range(konu, alt_konu):
    """Konu ve alt konu için ideal kelime aralığını belirle."""
    
    # RAG V3 kurallarına göre
    rules = {
        # Paragraf: 120-220
        ("paragraf", "ana_dusunce"): (120, 220),
        ("paragraf", "baslik_bulma"): (120, 220),
        ("paragraf", "anlatim_bicimi"): (120, 220),
        
        # Cümlede Anlam: 80-150
        ("cumlede_anlam", "sebep_sonuc"): (80, 150),
        ("cumlede_anlam", "kosul"): (80, 150),
        ("cumlede_anlam", "oznel_nesnel"): (80, 150),
        ("cumlede_anlam", "deyim"): (80, 150),
        
        # Sözcükte Anlam: 40-80 (numaralı cümleler)
        ("sozcukte_anlam", "cok_anlamlilik"): (40, 80),
        ("sozcukte_anlam", "es_anlamlilik"): (40, 80),
        ("sozcukte_anlam", "zit_anlamlilik"): (40, 80),
        
        # Dil Bilgisi: 100-180
        ("dil_bilgisi", "fiilimsiler"): (100, 180),
        ("dil_bilgisi", "kelime_turleri"): (100, 180),
        
        # Yazım: 80-150
        ("yazim_kurallari", "noktalama"): (80, 150),
        ("yazim_kurallari", "yazim_yanlisi"): (80, 150),
    }
    
    # Normalize
    konu_norm = konu.lower().replace(" ", "_").replace("ü", "u").replace("ö", "o").replace("ç", "c").replace("ı", "i").replace("ş", "s").replace("ğ", "g")
    alt_konu_norm = alt_konu.lower().replace(" ", "_").replace("ü", "u").replace("ö", "o").replace("ç", "c").replace("ı", "i").replace("ş", "s").replace("ğ", "g")
    
    key = (konu_norm, alt_konu_norm)
    
    # Eşleşme var mı?
    if key in rules:
        return rules[key]
    
    # Partial match (alt konu)
    for (k, ak), (min_w, max_w) in rules.items():
        if ak == alt_konu_norm or konu_norm in k:
            return (min_w, max_w)
    
    # Default
    return (80, 150)

def filter_data(input_path, output_path, strict_mode=True):
    """
    Veriyi filtrele.
    
    strict_mode=True: Sadece ideal aralıktaki örnekleri tut
    strict_mode=False: ±20% tolerans
    """
    
    data = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data.append(json.loads(line.strip()))
            except:
                pass
    
    print(f"📊 Toplam örnek: {len(data)}")
    
    # Filtrele
    filtered = []
    stats = {
        "total": len(data),
        "kept": 0,
        "too_short": 0,
        "too_long": 0,
        "no_rule": 0,
    }
    
    word_counts = []
    
    for example in data:
        user_text = example.get("user", "")
        assistant_text = example.get("assistant", "")
        
        # Konu/Alt Konu çıkar
        konu = None
        alt_konu = None
        
        if "Konu:" in user_text:
            konu = user_text.split("Konu:")[1].split("\n")[0].strip()
        if "Alt Konu:" in user_text:
            alt_konu = user_text.split("Alt Konu:")[1].split("\n")[0].strip()
        
        if not konu or not alt_konu:
            continue
        
        # Metin çıkar
        try:
            data_obj = json.loads(assistant_text)
            metin = data_obj.get("metin", "")
        except:
            continue
        
        wc = count_words(metin)
        word_counts.append(wc)
        
        # İdeal aralık
        min_w, max_w = get_word_count_range(konu, alt_konu)
        
        # Strict mode
        if strict_mode:
            if min_w <= wc <= max_w:
                filtered.append(example)
                stats["kept"] += 1
            elif wc < min_w:
                stats["too_short"] += 1
            else:
                stats["too_long"] += 1
        else:
            # ±20% tolerans
            tolerance = 0.2
            min_tolerant = int(min_w * (1 - tolerance))
            max_tolerant = int(max_w * (1 + tolerance))
            
            if min_tolerant <= wc <= max_tolerant:
                filtered.append(example)
                stats["kept"] += 1
            elif wc < min_tolerant:
                stats["too_short"] += 1
            else:
                stats["too_long"] += 1
    
    # Kaydet
    with open(output_path, 'w', encoding='utf-8') as f:
        for example in filtered:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    # İstatistikler
    print(f"\n{'='*60}")
    print(f"FİLTRELEME SONUÇLARI:")
    print(f"{'='*60}")
    print(f"Toplam:       {stats['total']}")
    print(f"✅ Tutuldu:   {stats['kept']} ({100*stats['kept']/stats['total']:.1f}%)")
    print(f"❌ Çok kısa:  {stats['too_short']} ({100*stats['too_short']/stats['total']:.1f}%)")
    print(f"❌ Çok uzun:  {stats['too_long']} ({100*stats['too_long']/stats['total']:.1f}%)")
    
    if word_counts:
        print(f"\n{'='*60}")
        print(f"KELİME SAYISI İSTATİSTİKLERİ (Orijinal):")
        print(f"{'='*60}")
        print(f"Ortalama:     {sum(word_counts)/len(word_counts):.1f}")
        print(f"Min:          {min(word_counts)}")
        print(f"Max:          {max(word_counts)}")
        
        # Filtered kelime sayıları
        filtered_wc = []
        for ex in filtered:
            try:
                data_obj = json.loads(ex.get("assistant", ""))
                metin = data_obj.get("metin", "")
                filtered_wc.append(count_words(metin))
            except:
                pass
        
        if filtered_wc:
            print(f"\n{'='*60}")
            print(f"KELİME SAYISI İSTATİSTİKLERİ (Filtrelenmiş):")
            print(f"{'='*60}")
            print(f"Ortalama:     {sum(filtered_wc)/len(filtered_wc):.1f}")
            print(f"Min:          {min(filtered_wc)}")
            print(f"Max:          {max(filtered_wc)}")
            
            # Dağılım
            ranges = {
                "<80": sum(1 for w in filtered_wc if w < 80),
                "80-120": sum(1 for w in filtered_wc if 80 <= w < 120),
                "120-150": sum(1 for w in filtered_wc if 120 <= w <= 150),
                "150-180": sum(1 for w in filtered_wc if 150 < w <= 180),
                ">180": sum(1 for w in filtered_wc if w > 180),
            }
            
            print(f"\nDAĞILIM:")
            for range_name, count in ranges.items():
                pct = 100 * count / len(filtered_wc) if filtered_wc else 0
                print(f"  {range_name:10s}: {count:4d} ({pct:5.1f}%)")
    
    print(f"\n✅ Filtrelenmiş veri kaydedildi: {output_path}")
    return stats

if __name__ == "__main__":
    import sys
    
    # Paths
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    data_dir = project_dir / "data"
    
    input_train = data_dir / "v11_filtered" / "train.jsonl"
    input_val = data_dir / "v11_filtered" / "val.jsonl"
    
    output_dir = data_dir / "v12_quality_filtered"
    output_dir.mkdir(exist_ok=True)
    
    output_train = output_dir / "train.jsonl"
    output_val = output_dir / "val.jsonl"
    
    print("🔄 DATA QUALITY FILTER - STRICT MODE")
    print("="*60)
    
    # Train
    print("\n📁 TRAIN SET:")
    print("-"*60)
    filter_data(input_train, output_train, strict_mode=True)
    
    # Val
    print("\n📁 VAL SET:")
    print("-"*60)
    filter_data(input_val, output_val, strict_mode=True)
    
    print("\n" + "="*60)
    print("✅ TEMİZLEME TAMAMLANDI!")
    print("="*60)
    print(f"\nYeni veri seti: {output_dir}")
    print(f"  - train.jsonl")
    print(f"  - val.jsonl")
