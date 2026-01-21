# -*- coding: utf-8 -*-
"""
LGS Türkçe Soru Şablonlama + Otomatik Dağılım + Referans Seçimi + Kalite Kontrol
==============================================================================
- Topic distribution / alt-topic distribution otomatik (JSON'dan)
- Türkçe karakter normalize: üöığşç -> uoigsc
- Kök kalıpları: el ile + veri tabanlı destek
- Negatif soru kökü tespiti
- Referans soru seçimi (aynı konu/alt konu + yakın yıl)
- Üretim sonrası "LGS filtresi" (şık uzunluğu, paralellik, tekrar, negatif uyumu vs.)
"""

from __future__ import annotations
import json
import random
import re
# import math  # (kullanılmıyor, gerekirse ekle)
from dataclasses import dataclass
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional, Any


# ---------------------------------------------------------------------
# 1) Türkçe normalize (senin kodundaki kritik bug burada)
# ---------------------------------------------------------------------
TR_MAP = str.maketrans({
    "ç": "c", "Ç": "c",
    "ğ": "g", "Ğ": "g",
    "ı": "i", "I": "i", "İ": "i",
    "ö": "o", "Ö": "o",
    "ş": "s", "Ş": "s",
    "ü": "u", "Ü": "u",
})

def normalize_key(text: str) -> str:
    """
    Normalize a topic string into a lowercase key without Turkish diacritics.

    This helper strips leading/trailing whitespace, converts Turkish characters to
    their ASCII equivalents via ``TR_MAP``, lowercases the text, replaces
    consecutive whitespace with underscores and removes any remaining
    non‑alphanumeric characters. The resulting string is suitable for use as a
    dictionary key when matching against ``STEM_PATTERNS``.

    :param text: Arbitrary topic name or phrase.
    :return: Normalized identifier composed of [a‑z0‑9_].
    """
    text = (text or "").strip().translate(TR_MAP).lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_]+", "", text)
    return text


def word_count(text: str) -> int:
    r"""
    Count the approximate number of words in a text.

    Words are defined as consecutive word characters (``\w``), which roughly
    correspond to sequences of letters/digits/underscores. This helper treats
    ``None`` or empty strings as containing zero words.

    :param text: Textual content to be counted.
    :return: Integer number of words found.
    """
    return len(re.findall(r"\w+", text or ""))


# ---------------------------------------------------------------------
# 2) El ile tanımlı kalıplar (seninkiler korunup iyileştirildi)
# ---------------------------------------------------------------------
STEM_PATTERNS = {
    "genel": [
        "Aşağıdakilerden hangisi {konu} ile ilgilidir?",
        "Aşağıdakilerden hangisidir?",
        "Bu metinde {odak} ile ilgili olarak aşağıdakilerden hangisi söylenebilir?",
    ],
    "paragraf": [
        "Bu metinde anlatılmak istenen aşağıdakilerden hangisidir?",
        "Bu metinle ilgili aşağıdakilerden hangisi söylenemez?",
        "Bu parçadan aşağıdaki yargıların hangisine ulaşılamaz?",
        "Bu metinden aşağıdaki yargıların hangisine ulaşılabilir?",
        "Bu metne en uygun başlık aşağıdakilerden hangisidir?",
        "Bu metnin türüyle ilgili aşağıdakilerden hangisi doğrudur?",
    ],
    "cumlede_anlam": [
        "Bu parçadaki numaralanmış cümlelerin hangisinde {anlam_turu} vardır?",
        "Bu cümlede anlatılmak istenen aşağıdakilerden hangisidir?",
        "Bu cümleye anlamca en yakın olan aşağıdakilerden hangisidir?",
        "Numaralanmış cümlelerin hangisinde koşul anlamı vardır?",
        "Numaralanmış cümlelerin hangisinde sebep-sonuç ilişkisi vardır?",
    ],
    "yazim_kurallari": [
        "Bu metindeki numaralanmış cümlelerin hangisinde yazım yanlışı yoktur?",
        "Aşağıdaki cümlelerin hangisinde yazım yanlışı vardır?",
        "Numaralanmış yerlerden hangisine {noktalama} getirilmelidir?",
        "Bu cümledeki altı çizili sözcükle ilgili aşağıdakilerden hangisi doğrudur?",
    ],
    "dil_bilgisi": [
        "Bu parçadaki numaralanmış sözcüklerden hangisi fiilimsi değildir?",
        "Aşağıdaki cümlelerin hangisinde anlatım bozukluğu yoktur?",
        "Bu cümlenin türüyle ilgili aşağıdakilerden hangisi yanlıştır?",
        "Altı çizili sözcüklerden hangisi yapım eki almıştır?",
    ],
    "sozcukte_anlam": [
        "\"{sozcuk}\" sözcüğü bu cümlelerde aşağıdaki anlamlarından hangisiyle kullanılmamıştır?",
        "Aşağıdaki cümlelerin hangisinde altı çizili sözcük terim anlamında kullanılmıştır?",
        "Bu parçada numaralanmış sözlerden hangisinin anlamı ayraç içinde verilen açıklamayla uyuşmamaktadır?",
    ],
    "cumle_olusturma": [
        "Bu cümlelerin anlamca doğru bir biçimde birleştirilmiş hâli aşağıdakilerden hangisidir?",
        "Bu metinde boş bırakılan yerlere düşüncenin akışına göre sırasıyla aşağıdakilerin hangisi getirilmelidir?",
        "Bu parçada numaralanmış boşluklara düşüncenin akışına göre aşağıdakilerden hangisi getirilmelidir?",
    ],
}


NEGATIVE_STEM_KEYWORDS = [
    "ulaşılamaz",
    "söylenemez",
    "değinilmemiştir",
    "yoktur",
    "değildir",
    "kullanılmamıştır",
    "uyuşmamaktadır",
    "bulunmaz",
    "örnek olamaz",
]

# Tembel/Genel seçenekler: öğrenciye ipucu veren veya soruyu anlamsızlaştıran seçenekler.
# Bu kalıplar seçenek analizi sırasında yakalanarak puanlama cezaları uygulanacaktır.
LAZY_OPTION_PATTERNS = [
    r"yukarıdak(ilerin|i) hepsi",    # "Yukarıdakilerin hepsi"/"Yukarıdaki hepsi" gibi
    r"yukarıdak(ilerin|i) hiçbiri",  # "Yukarıdakilerin hiçbiri"
    r"hiçbiri",                      # tek başına "Hiçbiri"
    r"hepsi",                        # tek başına "Hepsi"
    r"hiç bir(i)?",                  # ayrı yazılmış "hiç biri"
]

def is_negative_stem(stem: str) -> bool:
    s = (stem or "").lower()
    return any(k in s for k in NEGATIVE_STEM_KEYWORDS)


# ---------------------------------------------------------------------
# 3) Veri setinden otomatik istatistik (TOPIC_DISTRIBUTION vb.)
# ---------------------------------------------------------------------
@dataclass
class DatasetStats:
    topic_dist: Dict[str, float]
    question_type_dist: Dict[str, float]
    difficulty_dist: Dict[str, float]
    alt_topic_dist: Dict[str, Dict[str, float]]
    stem_phrase_freq: Dict[str, int]
    negative_ratio: float
    text_word_stats: Dict[str, float]
    topic_text_lengths: Dict[str, Dict[str, float]] # Konu bazlı metin uzunluğu istatistikleri
    option_len_stats: Dict[str, float]


def _normalize_dist(counter: Counter) -> Dict[str, float]:
    total = sum(counter.values()) or 1
    return {k: v / total for k, v in counter.items()}


def load_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSON veri seti liste formatında olmalı.")
    return data


def compute_stats(data: List[Dict[str, Any]]) -> DatasetStats:
    topic_c = Counter()
    qtype_c = Counter()
    diff_c = Counter()
    alt_c = defaultdict(Counter)

    stem_phrase = Counter()
    neg = 0

    text_word_counts = []
    topic_text_map = defaultdict(list) # Konulara göre metin uzunlukları
    option_lengths = []

    for d in data:
        topic = d.get("konu_basligi") or "Bilinmiyor"
        alt = d.get("alt_konu_basligi") or "Bilinmiyor"
        topic_c[topic] += 1
        alt_c[topic][alt] += 1

        qtype_c[d.get("soru_tipi") or "bilinmiyor"] += 1
        diff_c[d.get("zorluk") or "bilinmiyor"] += 1

        stem = d.get("soru_kökü") or ""
        if is_negative_stem(stem):
            neg += 1

        # stem phrase frekansı için kaba n-gram: en çok geçen kalıp parçaları
        for p in ["aşağıdakilerden hangisi", "bu metinde", "bu parçadan", "numaralanmış", "söylenemez", "ulaşılamaz"]:
            if p in stem.lower():
                stem_phrase[p] += 1

        metin = d.get("metin")
        if metin and metin != "yok":
            wc = word_count(metin)
            if wc > 5: # Çok kısa metinleri (örn: "Aşağıdaki cümlelerin...") yoksay
                text_word_counts.append(wc)
                topic_text_map[topic].append(wc)

        # şık uzunlukları
        for k in ["şık_a", "şık_b", "şık_c", "şık_d"]:
            opt = d.get(k)
            if isinstance(opt, str):
                option_lengths.append(len(opt.strip()))

    # metin istatistikleri
    if text_word_counts:
        tw_min = min(text_word_counts); tw_max = max(text_word_counts)
        tw_avg = sum(text_word_counts) / len(text_word_counts)
    else:
        tw_min = tw_max = tw_avg = 0

    if option_lengths:
        ol_min = min(option_lengths); ol_max = max(option_lengths)
        ol_avg = sum(option_lengths) / len(option_lengths)
    else:
        ol_min = ol_max = ol_avg = 0

    alt_topic_dist = {t: _normalize_dist(c) for t, c in alt_c.items()}

    # Konu bazlı ortalamalar
    topic_text_stats = {}
    for t, counts in topic_text_map.items():
        if counts:
            topic_text_stats[t] = {
                "avg": sum(counts) / len(counts),
                "min": min(counts),
                "max": max(counts)
            }
    
    return DatasetStats(
        topic_dist=_normalize_dist(topic_c),
        question_type_dist=_normalize_dist(qtype_c),
        difficulty_dist=_normalize_dist(diff_c),
        alt_topic_dist=alt_topic_dist,
        stem_phrase_freq=dict(stem_phrase),
        negative_ratio=(neg / (len(data) or 1)),
        text_word_stats={"min": tw_min, "max": tw_max, "avg": tw_avg, "count": len(text_word_counts)},
        topic_text_lengths=topic_text_stats,
        option_len_stats={"min": ol_min, "max": ol_max, "avg": ol_avg, "count": len(option_lengths)},
    )


# ---------------------------------------------------------------------
# 4) Konu/alt konu seçimi (senin kodunda yoktu)
# ---------------------------------------------------------------------
def weighted_choice(dist: Dict[str, float]) -> str:
    """
    Choose a random key from a probability distribution represented by a dict.

    :param dist: Dictionary mapping items to probabilities (not necessarily
                 normalised).
    :return: A single selected key.
    """
    keys = list(dist.keys())
    weights = list(dist.values())
    return random.choices(keys, weights=weights, k=1)[0]


def choose_topic(stats: DatasetStats, override_topic: Optional[str] = None) -> str:
    """
    Select a topic for question generation.

    :param stats: Precomputed dataset statistics containing topic distribution.
    :param override_topic: Optional specific topic to use.
    :return: Chosen topic string.
    """
    return override_topic if override_topic else weighted_choice(stats.topic_dist)


def choose_alt_topic(stats: DatasetStats, topic: str, override_alt: Optional[str] = None) -> str:
    """
    Select a subtopic (alt konu) for the given topic.

    :param stats: Dataset statistics containing per‑topic subtopic distributions.
    :param topic: Parent topic name.
    :param override_alt: Optional specific subtopic to use.
    :return: Chosen subtopic string.
    """
    if override_alt:
        return override_alt
    dist = stats.alt_topic_dist.get(topic)
    if not dist:
        return "Bilinmiyor"
    return weighted_choice(dist)


# ---------------------------------------------------------------------
# 5) Soru kökü kalıbı seçimi (normalize bug fix + fallback)
# ---------------------------------------------------------------------
TOPIC_TO_PATTERN_KEY = {
    # datasetinde konu isimleri farklıysa burayı genişlet
    "Paragraf": "paragraf",
    "Cümlede Anlam": "cumlede_anlam",
    "Yazım Kuralları": "yazim_kurallari",
    "Dil Bilgisi": "dil_bilgisi",
    "Sözcükte Anlam": "sozcukte_anlam",
    "Cümle Oluşturma": "cumle_olusturma",
}

def get_stem_patterns_for_topic(topic: str) -> List[str]:
    """
    Retrieve a list of question stem templates for a given topic.

    The function first attempts to map the provided topic to a canonical
    internal key (via ``TOPIC_TO_PATTERN_KEY``). If a match is found in
    ``STEM_PATTERNS``, the corresponding pattern list is returned. Otherwise,
    the topic is normalized with ``normalize_key`` and looked up directly.
    If no specific pattern list exists, a generic fallback is returned.

    :param topic: Human‑readable topic name (e.g., "Paragraf").
    :return: A list of stem template strings appropriate for the topic.
    """
    key = TOPIC_TO_PATTERN_KEY.get(topic)
    if key and key in STEM_PATTERNS:
        return STEM_PATTERNS[key]

    # normalize ederek doğrudan deneyelim
    n = normalize_key(topic)
    if n in STEM_PATTERNS:
        return STEM_PATTERNS[n]

    return STEM_PATTERNS["genel"]


# ---------------------------------------------------------------------
# 6) Referans soru seçimi (prompt şablonunda vardı, kodda yoktu)
# ---------------------------------------------------------------------
def pick_reference_questions(
    data: List[Dict[str, Any]],
    topic: str,
    alt_topic: str,
    target_year: Optional[int] = None,
    k: int = 4
) -> List[Dict[str, Any]]:
    """
    Select a small set of reference questions from the dataset.

    When generating a new question, it is useful to provide a few example
    questions with similar topic and subtopic. This function filters the
    dataset to prioritise items matching the requested ``topic`` and
    ``alt_topic``. If no exact matches exist, broader matches are allowed.
    When ``target_year`` is supplied, items are sorted by proximity to that
    year (so that more recent examples are prioritised). A maximum of
    ``k`` questions are returned.

    :param data: List of question records from the historical dataset.
    :param topic: Main topic to match ("konu_basligi").
    :param alt_topic: Subtopic to match ("alt_konu_basligi").
    :param target_year: Optional year used to bias selection toward nearby years.
    :param k: Maximum number of examples to return.
    :return: List of up to ``k`` question dictionaries.
    """
    pool = [d for d in data if d.get("konu_basligi") == topic and d.get("alt_konu_basligi") == alt_topic]
    if not pool:
        pool = [d for d in data if d.get("konu_basligi") == topic]
    if not pool:
        pool = data[:]

    if target_year is not None:
        def year_score(d):
            y = d.get("yıl")
            if not isinstance(y, int):
                return 999
            return abs(y - target_year)
        pool.sort(key=year_score)

        # yakınlardan biraz daha seçilebilir olsun diye ilk 25'i sınırla
        pool = pool[: min(len(pool), 25)]

    return random.sample(pool, k=min(k, len(pool)))


def format_reference_questions(refs: List[Dict[str, Any]]) -> str:
    """
    Format a list of reference questions for inclusion in the prompt.

    Each question's stem is enumerated with a numeric prefix. Only the
    "soru_kökü" field is used; other fields are ignored.

    :param refs: List of question dictionaries.
    :return: Multi‑line string with enumerated question stems.
    """
    lines: List[str] = []
    for i, d in enumerate(refs, 1):
        stem = (d.get("soru_kökü") or "").strip()
        lines.append(f"{i}) {stem}")
    return "\n".join(lines)


# ---------------------------------------------------------------------
# 7) Üretim promptu (seninki + ek açıklamalar + negatif uyumu)
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# 7) Gelişmiş Prompt Şablonları (Anlam vs Dil Bilgisi Ayrımı)
# ---------------------------------------------------------------------

# A) ANLAM VE PARAGRAF SORULARI İÇİN ŞABLON
# Amaç: Zengin, edebi, deneme veya hikaye tarzı metinler.
MEANING_PROMPT_TEMPLATE = """
Sen 15 yıllık deneyimli bir MEB LGS Türkçe soru yazarısın. Görevin, öğrencilerin anlama ve yorumlama becerilerini ölçen, LGS standartlarına %100 uygun sorular üretmektir.

## TEMEL KURALLAR
1. **Metin Kalitesi:** Edebi, ilgi çekici, 8. sınıf seviyesinde. Sıkıcı, ansiklopedik metinler YASAK.
2. **Soru Netliği:** Tek bir doğru cevap olmalı. Belirsizlik YASAK.
3. **Şık Dengesi:** Tüm şıklar benzer uzunlukta (fark <%20) ve yapıda olmalı.
4. **Türkçe Doğruluğu:** Dil bilgisi hatası YASAK. Noktalama kusursuz olmalı.
5. **LGS Formatı:** Gerçek LGS sorularının üslubunu ve yapısını taklit et.
6. **Planlama:** Soru yazmadan önce metni, kökü ve şıkları nasıl kurgulayacağını adım adım düşün; bu planlama sürecini cevapta gösterme (Chain‑of‑Thought düşüncesi yap fakat gizli tut).
7. **Genel Kültürden Kaçın:** Doğru cevap yalnızca metindeki bilgilerden çıkarılmalıdır. Metinde yer almayan bilgileri kullanma.
8. **Bilimsel ve Olgusal Doğruluk:** Metindeki bilgiler gerçek hayatla çelişmemeli.
9. **Halüsinasyon Engeli:** Metin ve şıklar tamamen senin yazdığın metne dayanmalı.

## GÖREV DETAYLARI
- **Konu:** {konu_basligi}
- **Alt Konu:** {alt_konu_basligi}
- **Zorluk:** {zorluk}
- **Soru Tipi:** {soru_tipi}

## METİN YAZIM KURALLARI
1. **TÜR:** Deneme, fıkra, makale veya öyküleyici anlatım.
2. **TEMA:** {tema} teması etrafında özgün içerik.
3. **UZUNLUK:** {metin_uzunlugu} kelime.
4. **TON:** Edebi, akıcı, öğrencinin ilgisini çekecek şekilde.
5. **YAPI:**
   - Giriş: İlgi çekici başlangıç
   - Gelişme: Düşünceyi derinleştir
   - Sonuç: Vurucu kapanış

## SORU KURGU
- Soru kökü: "{secilen_soru_koku}"
- Net, anlaşılır, tek cevaplı olmalı

## SEÇENEK KURALLARI
- 4 şık (A, B, C, D)
- **Doğru Cevap:** Metinden kanıtlanabilir
- **Çeldiriciler:** Mantıklı ama yanlış
- **Denge:** En uzun şık, en kısa şığın 1.2 katını geçmemeli

## PLANLAMA VE ÇIKARIM
Soruyu oluşturmadan önce, metni, kökü ve tüm şıkları düşünerek tasarla. Her adımı mantıklı bir akışla planla ve sadece sonuçta ortaya çıkan metni ve soruyu yaz. Düşünme sürecini ve notlarını paylaşma.

## FORMAT (AYNEN UYGULA)
Metin: [Edebi, ilgi çekici, {metin_uzunlugu} kelimelik metin]

Soru: {secilen_soru_koku}

A) [Şık - dengeli uzunlukta]
B) [Şık - dengeli uzunlukta]
C) [Şık - dengeli uzunlukta]
D) [Şık - dengeli uzunlukta]

Doğru Cevap: [A/B/C/D]

## ÖNEMLİ HATIRLATMALAR
❌ YAPMA: Kuru metinler, belirsiz sorular, dengesiz şıklar, Türkçe hatası
✅ YAP: Edebi metinler, net sorular, dengeli şıklar, kusursuz Türkçe
""".strip()

# B) DİL BİLGİSİ / YAZIM / NOKTALAMA İÇİN ŞABLON
# Amaç: Kuralı ANLATMAYAN, kuralı UYGULATAN normal bir metin içinde sorgulama.
GRAMMAR_PROMPT_TEMPLATE = """
Sen 15 yıllık deneyimli bir MEB LGS Türkçe soru yazarısın. Görevin, öğrencilerin dil bilgisi becerilerini ölçen, LGS standartlarına %100 uygun sorular üretmektir.

## TEMEL KURALLAR
1. **Metin:** Günlük hayattan, doğal dil kullanımı. Yapay örnekler YASAK.
2. **Soru:** Dil bilgisi kuralını DOĞRUDAN SORMAK YASAK. Metin içinde analiz yaptır.
3. **Şıklar:** Kısa, net, dengeli. Uzunluk farkı <%15.
4. **Türkçe:** Kusursuz. Dil bilgisi hatası YASAK.
5. **Planlama:** Soru ve metni yazmadan önce aklından adım adım plan yap. Bu Chain‑of‑Thought düşünce sürecini dışa vurma; yalnızca son ürünü yaz.
6. **Genel Kültürden Kaçın:** Sorunun cevabı yalnızca metindeki ipuçlarından çıkarılmalı.
7. **Bilimsel ve Olgusal Doğruluk:** Metindeki cümleler gerçek hayatla uyumlu olmalı.
8. **Halüsinasyon Engeli:** Doğru şık metinde açıkça bulunmalı; metin dışında bir bilgiyi "doğru" olarak verme.

## GÖREV DETAYLARI
- **Konu:** {konu_basligi}
- **Alt Konu:** {alt_konu_basligi}
- **Zorluk:** {zorluk}

## METİN YAZIM KURALLARI (KRİTİK!)
1. **YASAK:** "Fiilimsiler şöyledir..." gibi DERS NOTU metni ASLA YAZMA!
2. **DOĞRU:** Günlük hayattan, doğal bir paragraf yaz. Dil bilgisi kuralını DOĞAL şekilde içer.
3. **TEMA:** {tema} hakkında keyifli paragraf.
4. **UZUNLUK:** 40-60 kelime (kısa ve öz).
5. **NUMARALAMA:** Numaralanmış cümle formatı KULLANMA! Normal paragraf yaz.

## SORU KURGU
- Soru kökü: "{secilen_soru_koku}"
- Metin içinde ANALİZ yaptır, KURAL SORMA

## SEÇENEK KURALLARI
- 4 şık (A, B, C, D)
- Kısa, net ifadeler
- Doğru cevap %100 kesin olmalı

## FORMAT (AYNEN UYGULA)
Metin: [Günlük hayattan, doğal 40-60 kelimelik paragraf]

Soru: {secilen_soru_koku}

A) [Kısa şık]
B) [Kısa şık]
C) [Kısa şık]
D) [Kısa şık]

Doğru Cevap: [A/B/C/D]

## ÖNEMLİ
❌ "Fiilimsiler nedir?" gibi KURAL SORMA
❌ "Numaralanmış sözcüklerden hangisi..." gibi numaralı format KULLANMA
✅ "Altı çizili sözcüklerden hangisi fiilimsidir?" gibi ANALİZ YAPTIR

## PLANLAMA VE ÇIKARIM
Metni ve soruyu oluşturmadan önce, hangi dil bilgisi unsurunu doğal akışta vurgulayacağını adım adım düşün. Bu gizli düşünce sürecini paylaşıp yazma; yalnızca ortaya çıkan paragrafı, soruyu ve şıkları yaz.
""".strip()

def build_prompt(task: Dict[str, Any]) -> str:
    """
    Construct a system/user prompt pair for the language model.

    The input ``task`` dictionary contains metadata for a single question to
    generate, including available stem templates, chosen topic and subtopic,
    difficulty and type. A stem is selected at random from the provided
    candidates, the appropriate prompt template is filled with task
    parameters and any reference questions are appended. The resulting
    text is split into ``system`` and ``user`` parts for use with chat
    completion APIs (everything before the first blank line becomes the
    system message).

    :param task: Dictionary populated by ``build_generation_task``.
    :return: Dictionary with "system" and "user" keys containing prompt parts.
    """
    # 1. Soru kökünü seç (liste verildiyse birini seç, string ise direkt kullan)
    raw_stems = task.get("soru_koku_kaliplari", "")
    if isinstance(raw_stems, list):
        stem = random.choice(raw_stems)
    elif "\n" in raw_stems:
         # "- Kalıp 1\n- Kalıp 2" formatındaysa parçala ve seç
         stems = [s.strip("- ").strip() for s in raw_stems.split("\n") if s.strip()]
         stem = random.choice(stems) if stems else raw_stems
    else:
        stem = raw_stems
    
    # Task sözlüğüne seçilen kökü ekle
    task["secilen_soru_koku"] = stem
    
    # 2. Konuya göre şablon seç
    topic = task.get("konu_basligi", "")
    grammar_topics = ["Yazım Kuralları", "Noktalama İşaretleri", "Dil Bilgisi", "Fiilimsiler", "Cümle Öğeleri"]
    
    prompt_text = ""
    # Şablonu seç
    if any(g in topic for g in grammar_topics):
        prompt_text = GRAMMAR_PROMPT_TEMPLATE.format(**task)
    else:
        prompt_text = MEANING_PROMPT_TEMPLATE.format(**task)
    
    # 3. Referans soruları ekle
    if "referans_sorular" in task and task["referans_sorular"]:
        prompt_text += "\n\n## REFERANS SORULAR (ÖRNEK STİL)\nBu soruların zorluk seviyesini ve üslubunu örnek al:\n" + task["referans_sorular"]

    # System ve User ayrımı yap (API için)
    # Şablonlarımız "Sen usta bir MEB..." diye başlıyor.
    # İlk boş satıra kadar olan kısmı System, geri kalanını User yapacağız.
    parts = prompt_text.split("\n\n", 1)
    if len(parts) == 2:
        return {"system": parts[0], "user": parts[1]}
    else:
        return {"system": "Sen MEB LGS Türkçe soru uzmanısın.", "user": prompt_text}


# ---------------------------------------------------------------------
# 8) LGS Kalite Kontrol: üretim sonrası otomatik filtre/skor
# ---------------------------------------------------------------------
def option_parallelism_score(options: List[str]) -> float:
    """
    Compute a multi‑feature parallelism score for answer options.

    Traditional LGS soruları incelendiğinde çeldiricilerin biçimsel olarak
    birbirine benzemesi (uzunluk, cümle yapısı, fiil kullanımı vs.) önemlidir.
    Bu fonksiyon her şık için beş temel özellik çıkarır:

    1. **Sentence Ending** (bool) – cümle sonu noktalama işareti (.,!,?) var mı?
    2. **Capitalized Start** (bool) – ilk karakter büyük harf mi?
    3. **Verb Presence** (bool) – "–mak/–mek", "–yor", "–dır" gibi fiil ekleri içeriyor mu?
    4. **Lazy Phrase** (bool) – "hepsi", "hiçbiri" gibi tembel ifadeler içeriyor mu?
    5. **Long Phrase** (bool) – dört veya daha fazla kelime içeriyor mu?

    Her bir özellik için, en yaygın değerin toplam şıklar içindeki oranı hesaplanır. Sonuç
    özellik başına oranların ortalamasıdır. Dolayısıyla tüm özelliklerde tam uyum
    varsa puan 1.0, tamamen karışık ise daha düşük bir değer döner.

    :param options: Dört seçenek içeren liste.
    :return: 0.0–1.0 aralığında bir uyum skoru.
    """
    if not options:
        return 1.0
    shapes: List[Tuple[bool, bool, bool, bool, bool]] = []
    for opt in options:
        s = (opt or "").strip()
        ends_dot = bool(s.endswith((".", "!", "?")))
        starts_upper = bool(s[:1].isupper())
        has_verb = bool(re.search(r"\b(mak|mek|dır|dir|tır|tir|miştir|mıştır|yor|dı|di|du|dü)\b", s.lower()))
        has_lazy = bool(re.search(r"hepsi|hiçbiri|yukarıdak", s.lower()))
        is_long = word_count(s) >= 4
        shapes.append((ends_dot, starts_upper, has_verb, has_lazy, is_long))
    if not shapes:
        return 1.0
    feature_scores = []
    num_opts = len(shapes)
    for idx in range(len(shapes[0])):
        values = [shape[idx] for shape in shapes]
        mc = Counter(values).most_common(1)[0][1]
        feature_scores.append(mc / num_opts)
    return sum(feature_scores) / len(feature_scores)


# ---------------------------------------------------------------------
# Gelişmiş şık analiz fonksiyonları
# ---------------------------------------------------------------------
def lazy_option_penalty(options: List[str]) -> float:
    """
    Detect "tembel" (lazy) answer options that provide non‑informative
    meta‑choices such as "hepsi" or "hiçbiri". These choices often
    undermine the discriminative power of a question and should be discouraged.

    The function scans each option for patterns defined in ``LAZY_OPTION_PATTERNS``.
    If any pattern matches, a penalty proportional to the number of offending
    options is returned. If no lazy options are found, the penalty is zero.

    :param options: List of option texts in the order [A, B, C, D].
    :return: Float penalty between 0.0 and 1.0. A higher value indicates more
             severe misuse of lazy options.
    """
    if not options:
        return 0.0
    lazy_count = 0
    for opt in options:
        s = (opt or "").lower()
        for pattern in LAZY_OPTION_PATTERNS:
            if re.search(pattern, s):
                lazy_count += 1
                break
    return lazy_count / len(options)


def coverage_penalty(options: Dict[str, str], correct: str) -> float:
    """
    Compute a penalty if the correct answer's content is substantially
    duplicated within any of the distractors. Such "coverage" issues occur
    when a wrong option subsumes or repeats most of the correct answer,
    effectively hinting at the solution and reducing item quality.

    The penalty is based on token overlap. For each wrong option, we compute
    the Jaccard similarity between its token set and that of the correct
    answer. If the similarity exceeds 0.5 (i.e., more than half of the
    correct answer's tokens appear in the wrong option), it contributes to
    the penalty. The final penalty is the average of offending similarities.

    :param options: Mapping from choice label ("A".."D") to text.
    :param correct: Correct choice label (e.g., "B").
    :return: Float penalty between 0.0 and 1.0.
    """
    correct_text = options.get(correct, "")
    correct_tokens = set(re.findall(r"\w+", correct_text.lower().translate(TR_MAP)))
    if not correct_tokens:
        return 0.0
    overlaps = []
    for label, text in options.items():
        if label == correct:
            continue
        wrong_tokens = set(re.findall(r"\w+", (text or "").lower().translate(TR_MAP)))
        if not wrong_tokens:
            continue
        inter = wrong_tokens & correct_tokens
        sim = len(inter) / len(correct_tokens)
        if sim > 0.5:
            overlaps.append(sim)
    if not overlaps:
        return 0.0
    return sum(overlaps) / len(overlaps)


def option_length_penalty(options: List[str]) -> float:
    """
    Penalise large length discrepancies among answer options.

    A difference of up to 40 characters is considered acceptable. Differences
    above this threshold increase the penalty linearly. If there are no options,
    a neutral value of 1.0 is returned.

    :param options: List of answer option strings.
    :return: Penalty value in the range [0.0, 1.0], where values >0.6 indicate
             significant imbalance.
    """
    lens = [len((o or "").strip()) for o in options]
    if not lens:
        return 1.0
    span = max(lens) - min(lens)
    # span 0-40 arası makul; üstü cezalı
    return min(1.0, span / 80.0)


def repetition_penalty(options: List[str]) -> float:
    """
    Compute a penalty for excessive lexical overlap among answer options.

    Each option is tokenised into a set of unique lowercase words with
    diacritics normalised. Pairwise Jaccard similarities are computed for all
    option pairs. If the average similarity across pairs exceeds 0.35, the
    excess is returned as the penalty; otherwise zero.

    :param options: List of answer option strings.
    :return: Penalty value between 0 and 1.
    """
    token_sets = []
    for o in options:
        toks = set(re.findall(r"\w+", (o or "").lower().translate(TR_MAP)))
        token_sets.append(toks)
    overlaps = []
    for i in range(len(token_sets)):
        for j in range(i+1, len(token_sets)):
            inter = token_sets[i] & token_sets[j]
            union = token_sets[i] | token_sets[j]
            if union:
                overlaps.append(len(inter)/len(union))
    if not overlaps:
        return 0.0
    # ortalama overlap 0.35 üstüne çıkarsa cezala
    avg = sum(overlaps)/len(overlaps)
    return max(0.0, avg - 0.35)


def lgs_quality_check(
    metin: str,
    stem: str,
    options: Dict[str, str],
    correct: str,
    expected_text_words: Tuple[int, int] = (6, 99)
) -> Dict[str, Any]:
    """
    Evaluate the quality of a generated question using simple heuristics.

    This validator inspects the provided ``metin`` (text passage), ``stem``
    (question root), answer ``options`` and ``correct`` choice. It checks
    word counts, answer key validity, length differences, structural
    parallelism, repetition, lazy options, coverage errors and negative
    question stems. Each detected issue lowers an initial score of 100 by
    a weighted amount. A final score below 70 marks the question as
    unacceptable (``ok = False``).

    :param metin: Passage of text on which the question is based.
    :param stem: Question root string.
    :param options: Mapping of option labels (A–D) to answer strings.
    :param correct: The label of the correct option.
    :param expected_text_words: Allowed range for word count in the passage.
    :return: Report dictionary with ``ok``, ``issues`` and ``score`` keys.
    """
    opts = [options.get(k, "") for k in ["A", "B", "C", "D"]]
    report = {"ok": True, "issues": [], "score": 100}

    # metin uzunluğu
    if metin and metin != "yok":
        tw = word_count(metin)
        if tw < expected_text_words[0] or tw > expected_text_words[1]:
            report["issues"].append(f"Metin kelime sayısı aralık dışı: {tw}")
            report["score"] -= 8

    # doğru şık kontrol
    if correct not in ["A", "B", "C", "D"]:
        report["issues"].append("Doğru cevap A/B/C/D değil.")
        report["score"] -= 15

    # şık uzunluğu cezaları
    lp = option_length_penalty(opts)
    if lp > 0.6:
        report["issues"].append("Şık uzunluk farkı çok yüksek (bariz uzun/kısa şık var).")
        report["score"] -= int(20 * lp)

    # paralellik
    ps = option_parallelism_score(opts)
    if ps < 0.6:
        report["issues"].append("Şıklar biçimsel olarak paralel değil (cümle/ifade karışmış olabilir).")
        report["score"] -= int((0.6 - ps) * 30)  # daha büyük sapmalar için daha fazla ceza

    # tekrar
    rp = repetition_penalty(opts)
    if rp > 0:
        report["issues"].append("Şıklar birbirine aşırı benziyor (yüksek ortak kelime oranı).")
        report["score"] -= int(25 * rp)

    # tembel seçenekler
    lazy_pen = lazy_option_penalty(opts)
    if lazy_pen > 0:
        report["issues"].append("Tembel şık tespit edildi (hepsi/hiçbiri vb.).")
        report["score"] -= int(15 * lazy_pen)

    # kapsama hatası
    cov_pen = coverage_penalty(options, correct)
    if cov_pen > 0:
        report["issues"].append("Doğru cevabın ifadesi diğer şıklarda tekrar etmiş (kapsama hatası).")
        report["score"] -= int(25 * cov_pen)

    # negatif kök uyumu hatırlatma (tam doğrulama NLP ister)
    if is_negative_stem(stem):
        report["issues"].append("Negatif kök tespit edildi: doğru şık metinden çıkarılamayan olmalı (manuel kontrol önerilir).")
        report["score"] -= 3

    report["score"] = max(0, report["score"])
    if report["score"] < 70:
        report["ok"] = False

    return report


# ---------------------------------------------------------------------
# 9) Şablon örnek “task” üreticisi: topic/alt/kök/ref seçer
# ---------------------------------------------------------------------
def build_generation_task(
    data: List[Dict[str, Any]],
    stats: DatasetStats,
    target_year: Optional[int] = None,
    override_topic: Optional[str] = None,
    override_alt_topic: Optional[str] = None,
    tema_pool: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Construct an initial task description for question generation.

    This helper samples a topic and subtopic according to the dataset
    distributions, selects a question type and difficulty, estimates an
    appropriate text length, picks a thematic domain and assembles stem
    templates and reference questions. The returned dictionary serves as
    input to ``build_prompt``.

    :param data: List of existing question records for reference.
    :param stats: ``DatasetStats`` computed from the dataset.
    :param target_year: Optional year used to pick temporally close reference questions.
    :param override_topic: If provided, forces the main topic.
    :param override_alt_topic: If provided, forces the subtopic.
    :param tema_pool: Optional list of thematic seeds; defaults to a broad set.
    :return: Dictionary describing a generation task.
    """
    topic = choose_topic(stats, override_topic)
    alt = choose_alt_topic(stats, topic, override_alt_topic)

    # Soru tipi & zorluk: veri setinden çekilen dağılımla (zor = 0 olmasın diye güvenli fallback)
    soru_tipi = weighted_choice(stats.question_type_dist) if stats.question_type_dist else "yorumlama"
    zorluk = weighted_choice(stats.difficulty_dist) if stats.difficulty_dist else "orta"
    if zorluk == "bilinmiyor":
        zorluk = "orta"

    # metin uzunluğu: KONU BAZLI ortalama etrafında rastgele
    topic_stats = stats.topic_text_lengths.get(topic)
    if topic_stats:
        avg_len = topic_stats.get("avg", 45)
    else:
        # Fallback: global ortalama
        avg_len = stats.text_word_stats.get("avg", 45) or 45

    # Randomly sample around the average using a Gaussian; constrain to 20–120 words
    sampled_len = max(20, min(120, int(random.gauss(avg_len, 15))))

    # tema seç
    tema_choices = tema_pool or ["günlük yaşam", "bilim", "felsefe", "sanat", "toplum", "doğa"]
    tema = random.choice(tema_choices)

    # kök kalıpları
    patterns = get_stem_patterns_for_topic(topic)
    soru_koku_kaliplari = "\n".join([f"- {p}" for p in patterns])

    # referans sorular
    refs = pick_reference_questions(data, topic, alt, target_year=target_year, k=4)
    referans_sorular = format_reference_questions(refs)

    return {
        "konu_basligi": topic,
        "alt_konu_basligi": alt,
        "zorluk": zorluk,
        "soru_tipi": soru_tipi,
        "metin_uzunlugu": f"{sampled_len} - {sampled_len + 20} arası", # Model aralık sever
        "tema": tema,
        "soru_koku_kaliplari": soru_koku_kaliplari,
        "referans_sorular": referans_sorular,
    }





# ---------------------------------------------------------------------
# 10) Çalıştırma
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # 1) veri yükle
    import os
    # Dosya yolunu script konumuna göre ayarla
    script_dir = os.path.dirname(os.path.abspath(__file__))
    DATASET_PATH = os.path.join(script_dir, "..", "data", "merged_dataset_reclassified_fixed.json")
    data = load_dataset(DATASET_PATH)

    # 2) istatistik çıkar
    stats = compute_stats(data)

    # 3) örnek task & prompt
    task = build_generation_task(data, stats, target_year=2025)
    prompt = build_prompt(task)

    print("=== DATASET STATS (özet) ===")
    print("Topic dist (top 8):", dict(sorted(stats.topic_dist.items(), key=lambda x: -x[1])[:8]))
    print("QType dist:", stats.question_type_dist)
    print("Difficulty dist:", stats.difficulty_dist)
    print("Negative stem ratio:", round(stats.negative_ratio, 3))
    print("Text word stats:", stats.text_word_stats)

    print("\n=== SAMPLE GENERATION PROMPT ===\n")
    print(prompt)

    # 4) (Opsiyonel) üretim sonrası kalite kontrol örneği:
    dummy = {
        "metin": "Kısa bir metin örneği. İkinci cümle metni destekler.",
        "stem": "Bu metinden aşağıdaki yargıların hangisine ulaşılamaz?",
        "options": {"A": "Metin günlük yaşamdan söz eder.", "B": "Yazar doğaya değinir.", "C": "Metin bilimsel sonuçlar verir.", "D": "Metinde örnekler vardır."},
        "correct": "C",
    }
    qc = lgs_quality_check(dummy["metin"], dummy["stem"], dummy["options"], dummy["correct"])
    print("\n=== QUALITY CHECK (dummy) ===")
    print(qc)
