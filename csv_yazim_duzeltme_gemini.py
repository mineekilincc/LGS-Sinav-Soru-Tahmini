from __future__ import annotations
import argparse
import os
import sys
import time
import re
from typing import List, Optional

import pandas as pd

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    tqdm = None

try:
    import google.generativeai as genai
except ImportError:
    print("Hata: 'google-generativeai' paketi yüklü değil. Kurulum: pip install google-generativeai", file=sys.stderr)
    sys.exit(1)

DEFAULT_INPUT = r"C:\\Users\\Yusuf Uygur\\lgsTurkceDuzeltme\\guncel_veri_seti.csv"
DEFAULT_MODEL = "gemini-2.5-flash"
MAX_RETRIES = 5
TEMPERATURE = 0.0
DEFAULT_CONCURRENCY = max(1, min(4, os.cpu_count() or 1))
DEFAULT_BATCH_SIZE = 8

PROMPT_TEMPLATE = (
    "Biz bir ekip olarak LGS Turkce soru tahmin uygulamasi gelistiriyoruz. "
    "Elimizde 8 yillik cikmis sorular var ve veri toplama surecinde temizlik hatalari olustu. "
    "Metinlerde ve siklarda bazi kelimeler \"bira- kip\" gibi gereksiz tirelerle ayrildi, "
    "\"metin var mi\" gibi alanlarda \"evet\"/\"hayir\" ifadelerinin sonuna bosluk kondu ve "
    "bazi siklar alt satira duserek yapinin bozulmasina yol acti. "
    "Lutfen LGS soru mantigini koruyarak SADECE yazim, imla, noktalama ve gereksiz bosluk/tire hatalarini duzelt; "
    "anlami, secenek harflerini ve soru yapisini degistirme. "
    "Cikti olarak sadece duzeltilmis metni don ve metni bos birakma."
)

_ws_re = re.compile(r"\s+")
_punct_space_re = re.compile(r"\s+([,.;:!?%)])")

def cheap_normalize(s: str) -> str:
    s2 = s.strip()
    s2 = _ws_re.sub(" ", s2)
    s2 = _punct_space_re.sub(r"\1", s2)
    s2 = re.sub(r"\(\s+", "(", s2)
    return s2


def batched(seq, size: int):
    size = max(1, size)
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gemini ile CSV yazım düzeltme (tek dosya)")
    p.add_argument("--api-key", dest="api_key", type=str, help="Gemini API anahtarı (zorunlu değil: verilmezse etkileşimli sorulur)")
    p.add_argument("--input", dest="input_path", type=str, default=DEFAULT_INPUT, help="Girdi CSV yolu")
    p.add_argument("--output", dest="output_path", type=str, default=None, help="Çıktı CSV yolu (varsayılan: *_duzeltilmis.csv)")
    p.add_argument("--model", dest="model", type=str, default=DEFAULT_MODEL, help="Gemini model adı (örn. gemini-1.5-pro)")
    p.add_argument("--columns", nargs="*", default=None, help="Sadece bu sütunları düzelt (boş bırakılırsa tüm metin sütunları)")
    p.add_argument("--max-retries", dest="max_retries", type=int, default=MAX_RETRIES, help="Yeniden deneme sayısı")
    p.add_argument("--temperature", dest="temperature", type=float, default=TEMPERATURE, help="Model sicakligi (0 onerilir)")
    p.add_argument("--concurrency", dest="concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Ayni anda kac istegin gonderilecegi (varsayilan: dusuk ama hizli)")
    p.add_argument("--batch-size", dest="batch_size", type=int, default=DEFAULT_BATCH_SIZE, help="Her is parcasi ardarda kac metin duzeltecek")
    return p.parse_args()


def get_api_key(args_api_key: Optional[str]) -> str:
    if args_api_key:
        return args_api_key
    # Env yoksa etkileşimli iste
    try:
        return input("Gemini API anahtarını girin: ").strip()
    except KeyboardInterrupt:
        print("\nİptal edildi.")
        sys.exit(1)


def build_model(api_key: str, model_name: str):
    if not api_key:
        print("Hata: API anahtarı verilmedi.", file=sys.stderr)
        sys.exit(1)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def call_gemini(model, text: str, temperature: float, max_retries: int) -> str:
    prompt = f"{PROMPT_TEMPLATE}\n\nMetin: {text}"
    for attempt in range(1, max_retries + 1):
        try:
            resp = model.generate_content(prompt, generation_config={"temperature": temperature})
            return (resp.text or "").strip() or text
        except Exception:
            wait = min(2 ** attempt, 30)
            if attempt == max_retries:
                # Son denemede orijinali koru
                return text
            time.sleep(wait)


def main():
    args = parse_args()
    api_key = get_api_key(args.api_key)
    model = build_model(api_key, args.model)

    input_path = args.input_path
    if not os.path.exists(input_path):
        print(f"Hata: Girdi dosyası bulunamadı: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        df = pd.read_csv(input_path, dtype=str, keep_default_na=False)
    except Exception as e:
        print(f"CSV okunamadı: {e}", file=sys.stderr)
        sys.exit(1)

    # Çıktı yolu
    output_path = args.output_path
    if not output_path:
        stem, ext = os.path.splitext(input_path)
        output_path = f"{stem}_duzeltilmis{ext or '.csv'}"

    # Düzeltilecek sütunlar
    if args.columns:
        missing = [c for c in args.columns if c not in df.columns]
        if missing:
            print(f"Hata: CSV'de olmayan sütun(lar): {missing}", file=sys.stderr)
            sys.exit(1)
        columns_to_fix: List[str] = list(dict.fromkeys(args.columns))
    else:
        columns_to_fix = [c for c in df.columns if df[c].dtype == object]

    print("Düzeltilecek sütunlar:", columns_to_fix)

    # Görev listesi: yalnızca gerçekten düzeltilecek hücreleri iş parçasına ver
    text_positions: dict[str, list[tuple[int, int]]] = {}
    fix_col_indices = [df.columns.get_loc(c) for c in columns_to_fix]
    for r_idx, row in enumerate(df.itertuples(index=False, name=None)):
        for c_idx in fix_col_indices:
            val = row[c_idx]
            if val is None:
                continue
            s = str(val)
            if s.strip() == '' or s.strip() == '-':
                continue
            normalized = cheap_normalize(s)
            text_positions.setdefault(normalized, []).append((r_idx, c_idx))


    # Çıktı kopyası
    out_df = df.copy()

    # Paralel isleme
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def worker(batch: list[str]):
        results = []
        for text in batch:
            fixed = call_gemini(model, text, args.temperature, args.max_retries)
            results.append((text, fixed))
        return results

    tasks = list(text_positions.keys())
    total = len(tasks)
    prog = tqdm(total=total, desc='Hucreler duzeltiliyor') if tqdm else None

    batch_size = max(1, args.batch_size)

    if total:
        batches = list(batched(tasks, batch_size))
        max_workers = max(1, min(args.concurrency, len(batches)))
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            future_sizes = {}
            for batch in batches:
                fut = ex.submit(worker, batch)
                future_sizes[fut] = len(batch)
            for fut in as_completed(future_sizes):
                for text, fixed in fut.result():
                    for r_idx, c_idx in text_positions[text]:
                        out_df.iat[r_idx, c_idx] = fixed
                if prog:
                    prog.update(future_sizes[fut])

    if prog:
        prog.close()

    # Yaz
    try:
        out_df.to_csv(output_path, index=False)
    except Exception as e:
        print(f"Çıktı yazılamadı: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Bitti. Kaydedildi: {output_path}")


if __name__ == "__main__":
    main()
