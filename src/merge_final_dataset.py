# -*- coding: utf-8 -*-
"""
VERİ BİRLEŞTİRME VE FINAL DATASET
==================================
GPT soruları + v12_quality_filtered → v13_balanced_final
"""

import json
import re
from pathlib import Path
from collections import Counter

def count_words(text):
    """Kelime sayısını hesapla."""
    return len(re.findall(r'\b\w+\b', text or "", re.UNICODE))

def convert_gpt_to_jsonl(gpt_path, output_path):
    """GPT formatından bizim JSONL formatımıza çevir."""
    
    # GPT JSON'unu yükle
    with open(gpt_path, 'r', encoding='utf-8') as f:
        gpt_data = json.load(f)
    
    print(f"📊 GPT soruları yüklendi: {len(gpt_data)}")
    
    converted = []
    stats = {"total": len(gpt_data), "success": 0, "failed": 0}
    word_counts = []
    
    for item in gpt_data:
        try:
            konu = item.get("konu", "")
            alt_konu = item.get("alt_konu", "")
            
            # Assistant JSON oluştur
            assistant_obj = {
                "metin": item.get("metin", ""),
                "soru": item.get("soru", ""),
                "sik_a": item.get("sik_a", ""),
                "sik_b": item.get("sik_b", ""),
                "sik_c": item.get("sik_c", ""),
                "sik_d": item.get("sik_d", ""),
                "dogru_cevap": item.get("dogru_cevap", "")
            }
            
            # Kelime sayısı
            wc = count_words(assistant_obj["metin"])
            word_counts.append(wc)
            
            # JSONL formatı
            converted_item = {
                "user": f"Konu: {konu}\nAlt Konu: {alt_konu}\n\nBu kriterlere göre LGS Türkçe sorusu üret.",
                "assistant": json.dumps(assistant_obj, ensure_ascii=False)
            }
            
            converted.append(converted_item)
            stats["success"] += 1
            
        except Exception as e:
            print(f"   ❌ Hata: {str(e)}")
            stats["failed"] += 1
            continue
    
    # Kaydet
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in converted:
            f.write(json.dumps(item, ensure_ascii=False) + '\\n')
    
    print(f"\\n✅ Dönüştürme tamamlandı:")
    print(f"   Başarılı: {stats['success']}")
    print(f"   Başarısız: {stats['failed']}")
    print(f"   Kelime sayısı (ort): {sum(word_counts)/len(word_counts):.1f}")
    print(f"   Kaydedildi: {output_path}")
    
    return stats

def merge_datasets(v12_path, gpt_path, output_dir):
    """v12 + GPT → v13_balanced_final"""
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # v12 yükle
    v12_data = []
    with open(v12_path, 'r', encoding='utf-8') as f:
        for line in f:
            v12_data.append(json.loads(line.strip()))
    
    # GPT yükle
    gpt_data = []
    with open(gpt_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                gpt_data.append(json.loads(line))
            except Exception as e:
                print(f"   ⚠️ Satır parse edilemedi: {str(e)[:50]}")
                continue
    
    print(f"\\n{'='*70}")
    print(f"VERİ BİRLEŞTİRME")
    print(f"{'='*70}")
    print(f"v12_quality_filtered: {len(v12_data)}")
    print(f"GPT generated:        {len(gpt_data)}")
    print(f"Toplam:               {len(v12_data) + len(gpt_data)}")
    
    # Birleştir
    all_data = v12_data + gpt_data
    
    # Train/Val split (90/10)
    import random
    random.seed(42)
    random.shuffle(all_data)
    
    split_idx = int(len(all_data) * 0.9)
    train_data = all_data[:split_idx]
    val_data = all_data[split_idx:]
    
    # Kaydet
    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "val.jsonl"
    
    with open(train_path, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\\n')
    
    with open(val_path, 'w', encoding='utf-8') as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\\n')
    
    print(f"\\n✅ Birleştirme tamamlandı:")
    print(f"   Train: {len(train_data)} ({train_path})")
    print(f"   Val:   {len(val_data)} ({val_path})")
    
    # Dağılım analizi
    train_dist = Counter()
    for item in train_data:
        user = item.get("user", "")
        if "Konu:" in user and "Alt Konu:" in user:
            konu = user.split("Konu:")[1].split("\n")[0].strip()
            alt_konu = user.split("Alt Konu:")[1].split("\n")[0].strip()
            train_dist[f"{konu}_{alt_konu}"] += 1
    
    print(f"\\n{'='*70}")
    print(f"TRAIN DAĞILIMI:")
    print(f"{'='*70}")
    for key, count in sorted(train_dist.items()):
        print(f"   {key:50s}: {count:4d}")
    
    # Kelime sayısı analizi
    word_counts = []
    for item in train_data:
        try:
            assistant_obj = json.loads(item.get("assistant", "{}"))
            metin = assistant_obj.get("metin", "")
            wc = count_words(metin)
            word_counts.append(wc)
        except:
            pass
    
    if word_counts:
        print(f"\\n{'='*70}")
        print(f"KELİME SAYISI (TRAIN):")
        print(f"{'='*70}")
        print(f"   Ortalama: {sum(word_counts)/len(word_counts):.1f}")
        print(f"   Min:      {min(word_counts)}")
        print(f"   Max:      {max(word_counts)}")
        
        # Dağılım
        ranges = {
            "<50": sum(1 for w in word_counts if w < 50),
            "50-80": sum(1 for w in word_counts if 50 <= w < 80),
            "80-120": sum(1 for w in word_counts if 80 <= w < 120),
            "120-150": sum(1 for w in word_counts if 120 <= w <= 150),
            "150-180": sum(1 for w in word_counts if 150 < w <= 180),
            ">180": sum(1 for w in word_counts if w > 180),
        }
        
        print(f"\\n   DAĞILIM:")
        for range_name, count in ranges.items():
            pct = 100 * count / len(word_counts)
            print(f"      {range_name:10s}: {count:4d} ({pct:5.1f}%)")
    
    return {
        "train": len(train_data),
        "val": len(val_data),
        "total": len(all_data)
    }

if __name__ == "__main__":
    project_dir = Path(__file__).parent.parent
    
    # Paths
    gpt_json = project_dir / "data" / "questions.json"
    gpt_jsonl = project_dir / "data" / "temp" / "gpt_converted_fixed.jsonl"
    v12_train = project_dir / "data" / "v12_quality_filtered" / "train.jsonl"
    output_dir = project_dir / "data" / "v13_balanced_final"
    
    gpt_jsonl.parent.mkdir(exist_ok=True)
    
    print("="*70)
    print("FINAL DATASET OLUŞTURMA")
    print("="*70)
    
    # 1. GPT formatını dönüştür
    print("\\n1️⃣ GPT formatı dönüştürülüyor...")
    convert_gpt_to_jsonl(gpt_json, gpt_jsonl)
    
    # 2. Birleştir
    print("\\n2️⃣ Veri setleri birleştiriliyor...")
    result = merge_datasets(v12_train, gpt_jsonl, output_dir)
    
    print(f"\\n{'='*70}")
    print(f"✅ FINAL DATASET HAZIR!")
    print(f"{'='*70}")
    print(f"Klasör: {output_dir}")
    print(f"Train:  {result['train']} örnek")
    print(f"Val:    {result['val']} örnek")
    print(f"Toplam: {result['total']} örnek")
