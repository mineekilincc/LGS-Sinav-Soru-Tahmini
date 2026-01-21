# -*- coding: utf-8 -*-
"""GPT JSON'u düzgün JSONLe çevir"""
import json
from pathlib import Path

project_dir = Path(__file__).parent.parent

# GPT JSON array'ini yükle
with open(project_dir / "data" / "questions.json", encoding='utf-8') as f:
    gpt_array = json.load(f)

print(f"📊 Toplam GPT sorusu: {len(gpt_array)}")

# Her soruyu ayrı satıra yaz
output_file = project_dir / "data" / "temp" / "gpt_converted_fixed.jsonl"
output_file.parent.mkdir(exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    for question in gpt_array:
        # Bizim formatımıza çevir
        item = {
            "user": f"Konu: {question['konu']}\nAlt Konu: {question['alt_konu']}\n\nBu kriterlere göre LGS Türkçe sorusu üret.",
            "assistant": json.dumps({
                "metin": question.get("metin", ""),
                "soru": question.get("soru", ""),
                "sik_a": question.get("sik_a", ""),
                "sik_b": question.get("sik_b", ""),
                "sik_c": question.get("sik_c", ""),
                "sik_d": question.get("sik_d", ""),
                "dogru_cevap": question.get("dogru_cevap", "")
            }, ensure_ascii=False)
        }
        
        # HER SATIR AYRI!
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"✅ JSONL dosyası oluşturuldu: {output_file}")
print(f"   Toplam satır: {len(gpt_array)}")
