"""Eksik kalan canonical_subtopic / question_type gruplarini guvenli sekilde cogalt.

Bu script, serbest (kontrolsuz) sentetik veri uretimini bilerek engeller.
Uretilen her aday:
  - JSON parse
  - HardValidator
  - TypeRuleValidator
kontrollerinden gecmeden dataset'e eklenmez.

Kullanim (ornek):
  python scripts/augment_missing.py \
    --in data/processed/train_balanced_v1.jsonl \
    --out data/processed/train_balanced_v2.jsonl \
    --group_key canonical_subtopic \
    --min_count 20 \
    --n_candidates 5

Not:
  ModelClient su an stub. Bu scriptin calismasi icin `src/lgs_engine/model/client.py`
  dosyasini kendi Colab inference server'ina baglamalisin.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from lgs_engine.core.pipeline import GenerationPipeline
from lgs_engine.model.client import ModelClient


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def write_jsonl(path: Path, items: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def build_prompt(seed: Dict[str, Any]) -> str:
    """Seed soruyu kullanarak hedef grupta yeni bir soru isteme prompt'u.

    Serbest kopyalamayi azaltmak icin:
    - Sadece tip/konu/subtopic iskeletini aliyoruz.
    - Metni/serileri aynen kopyalamayi yasakliyoruz.
    """
    topic_family = seed.get("topic_family", "")
    subtopic = seed.get("canonical_subtopic", "")
    qtype = seed.get("question_type", "")
    return (
        "Sadece GECERLI JSON uret. JSON disinda hicbir sey yazma.\n"
        "Ayni anahtarlari kullan: text, highlight, stem, choices(A,B,C,D), answer, topic_family, canonical_subtopic, question_type.\n"
        "Kopyalama YASAK: onceki sorulardaki metni veya secenekleri kopyalama.\n"
        f"Hedef: topic_family={topic_family}, canonical_subtopic={subtopic}, question_type={qtype}.\n"
        "LGS Turkce tarzinda, tek dogru cevapli, cozumlenebilir bir soru uret."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--group_key", choices=["canonical_subtopic", "question_type"], default="canonical_subtopic")
    ap.add_argument("--min_count", type=int, default=20)
    ap.add_argument("--n_candidates", type=int, default=5)
    ap.add_argument("--base_url", type=str, default=None, help="Model server base URL (optional)")
    args = ap.parse_args()

    inp = Path(args.inp)
    out = Path(args.out)

    data = read_jsonl(inp)
    counts = Counter([d.get(args.group_key, "") for d in data])
    groups = defaultdict(list)
    for d in data:
        groups[d.get(args.group_key, "")].append(d)

    need = {k: args.min_count - v for k, v in counts.items() if k and v < args.min_count}
    if not need:
        print("No augmentation needed.")
        write_jsonl(out, data)
        return

    print("Need augmentation:")
    for k, v in sorted(need.items(), key=lambda x: -x[1]):
        print(f"  {k}: +{v}")

    model = ModelClient(base_url=args.base_url)
    pipeline = GenerationPipeline(model=model)

    augmented: List[Dict[str, Any]] = []
    for group, add_n in need.items():
        seeds = groups[group]
        if not seeds:
            continue

        produced = 0
        seed_idx = 0
        while produced < add_n:
            seed = seeds[seed_idx % len(seeds)]
            seed_idx += 1
            prompt = build_prompt(seed)
            try:
                q = pipeline.generate_best(prompt, n=args.n_candidates)
            except Exception:
                continue

            # grup anahtari zorunlu sabitle
            q[args.group_key] = group
            augmented.append(q)
            produced += 1

    merged = data + augmented
    write_jsonl(out, merged)
    print(f"Wrote {len(merged)} rows -> {out}")


if __name__ == "__main__":
    main()
