import re

U_TAG_RE = re.compile(r"\[u\](.*?)\[/u\]", flags=re.IGNORECASE | re.DOTALL)

def word_count(s: str) -> int:
    return len(re.findall(r"\b\w+\b", s or "", flags=re.UNICODE))

def sentence_count(s: str) -> int:
    # Basit cumle sayaci (TR icin yeterli baseline)
    if not s:
        return 0
    parts = re.split(r"[.!?]+", s)
    return sum(1 for p in parts if p.strip())

def has_repetition_loop(s: str, window: int = 3) -> bool:
    """Ardisik cumle tekrarlarini yakalar."""
    if not s:
        return False
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", s) if x.strip()]
    if len(sentences) < 4:
        return False
    for i in range(len(sentences) - window):
        block = sentences[i:i+window]
        next_block = sentences[i+window:i+2*window]
        if block == next_block and block:
            return True
    return False

def extract_u_tag_spans(s: str) -> list[str]:
    """[u]...[/u] ile isaretlenen parcalari cikarir."""
    if not s:
        return []
    return [m.group(1).strip() for m in U_TAG_RE.finditer(s) if m.group(1).strip()]

def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def highlight_appears_in_text(text: str, highlight: str) -> bool:
    """Highlight'in metinde gecip gecmedigini kontrol eder.

    - [u]...[/u] icinde geciyorsa kabul.
    - Metnin duz halinde geciyorsa kabul.
    """
    if not highlight:
        return False
    t = normalize_ws(text)
    h = normalize_ws(highlight)
    if not t or not h:
        return False
    # u-tag icinde var mi?
    for span in extract_u_tag_spans(t):
        if normalize_ws(span) == h:
            return True
    # duz metinde var mi?
    return h in t
