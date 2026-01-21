# -*- coding: utf-8 -*-
"""
LGS Veri Seti Düzeltme Aracı
============================
Tespit edilen hatalı kayıtları düzeltir.
"""

import json
import os

def fix_dataset_file(file_path):
    # Eğer dosya pkl veya json değilse atla veya json yükle hatası almamak için
    if not file_path.endswith('.json'):
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
    except Exception as e:
        print(f"Skipping {os.path.basename(file_path)}: {e}")
        return

    # Liste değilse (örn. obje ise) atla
    if not isinstance(content, list):
        return
    
    # İçinde soru_id yoksa atla
    if not content or not isinstance(content[0], dict) or "soru_id" not in content[0]:
        return

    print(f"🛠️  Taranıyor: {os.path.basename(file_path)}")
    data = content
    updates = 0
    
    for item in data:
        sid = item.get("soru_id")
        
        # 1. LGSTR-2024-1-A-07: Noktalama -> Paragraf (Söz Öbeği)
        if sid == "LGSTR-2024-1-A-07":
            item["konu_basligi"] = "Sözcükte Anlam"
            item["alt_konu_basligi"] = "Söz Öbeğinde Anlam"
            print(f"✅ {sid} düzeltildi: Sözcükte Anlam / Söz Öbeğinde Anlam")
            updates += 1
            
        # 2. LGSTR-2024-1-A-10: Noktalama -> Metin Türleri
        elif sid == "LGSTR-2024-1-A-10":
            item["konu_basligi"] = "Metin Türleri"
            item["alt_konu_basligi"] = "Metin Türleri"
            print(f"✅ {sid} düzeltildi: Metin Türleri")
            updates += 1
            
        # 3. LGSTR-2024-1-A-20: Noktalama -> Cümle Türleri
        elif sid == "LGSTR-2024-1-A-20":
            item["konu_basligi"] = "Cümle Türleri"
            item["alt_konu_basligi"] = "Cümle Çeşitleri"
            print(f"✅ {sid} düzeltildi: Cümle Türleri")
            updates += 1
            
        # 4. LGSTR-2025-1-A-12: Noktalama -> Paragraf (Ana Düşünce)
        elif sid == "LGSTR-2025-1-A-12":
            item["konu_basligi"] = "Paragraf"
            item["alt_konu_basligi"] = "Ana Düşünce"
            print(f"✅ {sid} düzeltildi: Paragraf / Ana Düşünce")
            updates += 1
            
        # 5. LGSTR-2021-1-A-14: Noktalama -> Paragraf (Yapı)
        elif sid == "LGSTR-2021-1-A-14":
            item["konu_basligi"] = "Paragraf"
            item["alt_konu_basligi"] = "Paragrafın Yapısı"
            print(f"✅ {sid} düzeltildi: Paragraf / Paragrafın Yapısı")
            updates += 1
            
        # 6. LGSTR-2023-1-A-02: Şık Hatası (II, II -> II, III)
        elif sid == "LGSTR-2023-1-A-02":
            if item.get("şık_c") == "II":
                item["şık_c"] = "III"
                print(f"✅ {sid} düzeltildi: Şık C (II -> III)")
                updates += 1

        # 7. LGSTR-2020-1-A-02: Paragraf -> Söz Sanatları
        elif sid == "LGSTR-2020-1-A-02":
            item["konu_basligi"] = "Söz Sanatları"
            item["alt_konu_basligi"] = "Söz Sanatları"
            print(f"✅ {sid} düzeltildi: Söz Sanatları")
            updates += 1

        # 8. LGSTR-2025-1-A-20: Paragraf -> Cümle Türleri
        elif sid == "LGSTR-2025-1-A-20":
            item["konu_basligi"] = "Cümle Türleri"
            item["alt_konu_basligi"] = "Cümle Çeşitleri"
            print(f"✅ {sid} düzeltildi: Cümle Türleri")
            updates += 1
    
    # Kaydet
    if updates > 0:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Toplam {updates} kayıt güncellendi ve kaydedildi.")
    else:
        print("\n⚠ Hiçbir değişiklik yapılmadı (zaten düzeltilmiş olabilir).")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    data_dir = os.path.join(project_dir, "data")
    
    print(f"📂 Veri klasörü taranıyor: {data_dir}")
    
    for filename in os.listdir(data_dir):
        file_path = os.path.join(data_dir, filename)
        fix_dataset_file(file_path)
