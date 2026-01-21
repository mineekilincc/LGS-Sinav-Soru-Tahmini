# LGS Soru Engine (v1)

Bu repo, LGS Turkce icin **kontrollu soru uretimi** (fine-tune + RAG + validator) pipeline'i icin temel iskelet sunar.

Bu projede "tek atis" yerine bilincli olarak **rejection sampling** kullanilir:
1) N aday üret
2) Validator ile ele
3) En iyi adayi sec

Bu sayede su hatalar sistemsel olarak azaltılır:
- Altı çizili (underline) istenip metinde olmaması
- Cumlede anlam gibi tiplerde paragraf uretilmesi
- Repetition loops
- Eksik/bozuk JSON

## Hedef
- UI secimleri (opsiyonel): `topic_family` (Paragraf, Cumlede Anlam, ...)
- Sistem secimleri: `canonical_subtopic`, `question_type`
- Cikti: Her zaman ayni JSON semasi
- Kalite garantisi: `validator + repair + n-aday secimi`

## Veri
`data/processed/` altinda:
- `normalized_merged_v2.jsonl` : normalize edilmis tum veri
- `train_balanced_v1.jsonl` / `val_balanced_v1.jsonl` / `test_balanced_v1.jsonl`
- `balanced_v1_report.txt`
- `mapping_raw_to_canonical_v1.csv`

## Question Type Contract
`configs/question_type_rules.yaml` dosyasi, her `question_type` icin zorunlu kurallari tanimlar.
Validator bu dosyaya gore karar verir. Underline tiplerinde `highlight` zorunludur ve metinde gecmek zorundadir.

## Eksik alt konulari cogaltma (kontrollu)
Serbest sentetik üretim yerine validator kontrollu augment:

```bash
python scripts/augment_missing.py \
  --in data/processed/train_balanced_v1.jsonl \
  --out data/processed/train_balanced_v2.jsonl \
  --group_key canonical_subtopic \
  --min_count 20 \
  --n_candidates 5 \
  --base_url http://localhost:8001
```

## Calistirma (lokal)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.api.main:app --reload
```

## API
- `POST /generate` : prompt + opsiyonel `topic_family` alir, validator'dan gecen en iyi soruyu dondurur.

> Not: Model entegrasyonu su an iskelet (stub). Colab'daki model server ya da local inference baglanacak.
