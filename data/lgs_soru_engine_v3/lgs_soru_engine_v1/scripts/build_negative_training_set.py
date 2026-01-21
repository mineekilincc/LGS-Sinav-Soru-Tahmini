#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hard negatives -> Negative training set builder

Amaç:
- data/hard_negatives.jsonl içindeki başarısız üretimleri al
- fine-tune için "Düzelt ve sadece JSON üret" formatında eğitim örnekleri üret

Çıktı:
- out_jsonl: chat-format JSONL (her satır: {"messages":[...]} )
- Ayrıca rapor: kaç kayıt işlendi, kaç tanesi üretildi, hangi hatalar baskın

Notlar:
- Bu script "gerçek doğru cevabı" üretmeye çalışmaz.
  Çünkü hard_negatives çoğu zaman hatalı/eksik içerik taşır.
- Negative training hedefi:
  1) JSON disiplinini artırmak
  2) Tip sözleşmesine uyumu artırmak
  3) Underline/highlight gibi şartları unutmamayı öğretmek
  4) Boş/çok kısa/dup şık/loop gibi hataları azaltmak
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ----- templates -----

SYSTEM_PROMPT = (
    "Sen LGS Türkçe soru düzeltme asistanısın.\n"
    "Kurallar:\n"
    "- SADECE geçerli JSON döndür.\n"
    "- JSON şemasını bozma, anahtar isimlerini değiştirme.\n"
    "- question_type alanına uy.\n"
    "- Gerekiyorsa highlight/underline şartlarını düzelt.\n"
    "- Gereksiz açıklama yazma.\n"
)

# Bu prompt, modele "bozuk JSON / hatalı içerik" verip düzeltmesini ister.
# Burada özellikle underline ve tip uyumu gibi sistemsel hataları hedefliyoruz.
USER_TEMPLATE = (
    "Aşağıdaki içerik bir LGS Türkçe sorusu üretim çıktısıdır ama hatalıdır.\n"
    "Hatalar (etiketler): {errors}\n\n"
    "Görev:\n"
    "1) Bu soruyu mümkün olan en az değişiklikle düzelt.\n"
    "2) SADECE geçerli JSON döndür.\n"
    "3) Eğer altı çizili/underline gerekiyorsa:\n"
    "   - highlight boşsa text içinden 3-8 kelimelik bir ifade seç.\n"
    "   - highlight text içinde birebir geçsin.\n"
    "   - text içinde highlight'ın geçtiği ilk yeri [u]...[/u] ile işaretle.\n\n"
    "Girdi:\n"
    "{payload}\n"
)

# Modelin döndürmesini istediğimiz minimum şema (anahtarlar sabit kalsın diye yönlendirici)
# Not: datasetinizde ek alanlar varsa script onları kaldırmaz; sadece hedefi yönlendirir.
ASSISTANT_HINT = (
    "JSON anahtarları örnek: "
    '{"metin":"","highlight":"","soru":"","sik_a":"","sik_b":"","sik_c":"","sik_d":"","dogru_cevap":"A","question_type":""}'
)


# ----- helpers -----

def safe_json_dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                # bozuk satır -> atla
                continue
    return rows


def pick_payload(rec: Dict[str, Any]) -> str:
    """
    Negatif kayıtta mümkün olduğunca 'parsed' JSON'u kullanmak isteriz.
    Yoksa 'raw' metni kullanırız.
    """
    if isinstance(rec.get("parsed"), dict):
        return safe_json_dumps(rec["parsed"])
    raw = rec.get("raw")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    # en son: tüm record
    return safe_json_dumps(rec)


def normalize_error_list(errors: Any) -> List[str]:
    if errors is None:
        return []
    if isinstance(errors, list):
        return [str(e) for e in errors if str(e)]
    if isinstance(errors, str):
        return [errors]
    return [str(errors)]


def should_keep_stage(stage: str) -> bool:
    """
    Hangi stage'lerden negative training üretelim?

    - json_parse_failed: ham metinden JSON'a dönmeyi öğretir
    - hard_fail: şık/cevap/loop/çok kısa gibi hataları azaltır
    - type_fail / highlight_*: tip sözleşmesi + underline öğretir
    - semantic_fail: çözülemez/uyumsuz soruları azaltır (kısmen)
    """
    keep = {
        "json_parse_failed",
        "json_repair_failed",
        "hard_fail",
        "type_fail",
        "type_fail_after_highlight_repair",
        "type_fail_highlight_repair_unavailable",
        "semantic_fail",
    }
    return stage in keep


def build_example(rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    stage = str(rec.get("stage", "")).strip()
    if not should_keep_stage(stage):
        return None

    errors = normalize_error_list(rec.get("errors"))

    # stage bazlı ek etiketler
    tags = set(errors)
    if stage.startswith("json"):
        tags.add("needs_json_only")
    if "highlight" in stage or "highlight_required" in tags or "highlight_not_in_text" in tags:
        tags.add("needs_highlight_fix")

    payload = pick_payload(rec)
    user_msg = USER_TEMPLATE.format(errors=", ".join(sorted(tags)) or stage, payload=payload)

    example = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
            # Assistant mesajı boş bırakılır: SFT hedefi, modelin doğru JSON üretmesi.
            # Bazı trainer'lar empty assistant istemez; bu durumda aşağıdaki placeholder'ı kullanma:
            # {"role":"assistant","content":"<TARGET_JSON_HERE>"}
        ]
    }

    # Not: Burada assistant target yok; çünkü bu scriptin amacı "training prompt set" üretmek.
    # Eğer "teacher ile düzeltip target üretmek" istersen, ayrı pipeline gerekir (bir sonraki adım).
    return example


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--in",
        dest="in_path",
        required=True,
        help="hard_negatives.jsonl yolu (ör. data/hard_negatives.jsonl)",
    )
    ap.add_argument(
        "--out",
        dest="out_path",
        required=True,
        help="çıktı jsonl yolu (ör. data/negative_training_prompts.jsonl)",
    )
    ap.add_argument(
        "--max",
        dest="max_items",
        type=int,
        default=5000,
        help="maksimum örnek sayısı (varsayılan 5000)",
    )
    ap.add_argument(
        "--dedup",
        dest="dedup",
        action="store_true",
        help="Aynı payload+errors kombinasyonlarını tekilleştir",
    )
    args = ap.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = load_jsonl(in_path)

    stage_counts = Counter()
    error_counts = Counter()
    kept = 0
    written = 0

    seen = set()

    with out_path.open("w", encoding="utf-8") as f:
        for rec in rows:
            if written >= args.max_items:
                break

            stage = str(rec.get("stage", "")).strip()
            stage_counts[stage] += 1

            errs = normalize_error_list(rec.get("errors"))
            for e in errs:
                error_counts[e] += 1

            ex = build_example(rec)
            if not ex:
                continue
            kept += 1

            if args.dedup:
                payload = pick_payload(rec)
                key = (stage, tuple(sorted(errs)), payload[:500])  # ilk 500 char ile dedup
                if key in seen:
                    continue
                seen.add(key)

            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
            written += 1

    # report
    report_path = out_path.with_suffix(".report.txt")
    lines: List[str] = []
    lines.append(f"Input:  {in_path}")
    lines.append(f"Output: {out_path}")
    lines.append(f"Total input rows: {len(rows)}")
    lines.append(f"Kept rows:        {kept}")
    lines.append(f"Written rows:     {written}")
    lines.append("")
    lines.append("Top stages:")
    for k, v in stage_counts.most_common(20):
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("Top errors:")
    for k, v in error_counts.most_common(30):
        lines.append(f"  {k}: {v}")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
