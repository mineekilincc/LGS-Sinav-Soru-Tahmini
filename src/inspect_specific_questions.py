import json
import os

def inspect_questions(file_path, target_ids):
    print(f"🔍 Dosya okunuyor: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    found_count = {}
    for i, item in enumerate(data):
        sid = item.get("soru_id")
        if sid in target_ids:
            if sid not in found_count:
                found_count[sid] = 0
            found_count[sid] += 1
            
            print(f"\n{'='*50}")
            print(f"INDEX: {i}")
            print(f"ID: {sid}")
            print(f"Konu: {item.get('konu_basligi')}")
            print(f"Alt Konu: {item.get('alt_konu_basligi')}")
            print(f"Soru Kökü: {item.get('soru_kökü')}")
            print(f"Metin: {item.get('metin')[:200]}..." if item.get('metin') else "YOK")
            print(f"Şık A: {item.get('şık_a')}")
            print(f"Şık B: {item.get('şık_b')}")
            print(f"Şık C: {item.get('şık_c')}")
            print(f"Şık D: {item.get('şık_d')}")
            print(f"Cevap: {item.get('doğru_cevap')}")
            print(f"{'='*50}")
            
    print(f"\n✅ Tarama tamamlandı.")
    for tid in target_ids:
        count = found_count.get(tid, 0)
        if count > 1:
            print(f"🚨 DUPLICATE ID BULUNDU: {tid} ({count} defa)")
        elif count == 0:
            print(f"❌ ID BULUNAMADI: {tid}")

if __name__ == "__main__":
    target_ids = [
        "LGSTR-2024-1-A-07",
        "LGSTR-2024-1-A-10",
        "LGSTR-2024-1-A-20",
        "LGSTR-2025-1-A-12",
        "LGSTR-2023-1-A-02",
        "LGSTR-2021-1-A-14",
        "LGS-TR-2025-47",
        "LGS-TR-2025-61",
        "ODGSM-2021-2022-EKİM-09"
    ]
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    data_path = os.path.join(project_dir, "data", "merged_dataset.json")
    
    inspect_questions(data_path, target_ids)
