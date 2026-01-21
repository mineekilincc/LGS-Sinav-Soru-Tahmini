# -*- coding: utf-8 -*-
"""
AKILLI RAG SİSTEMİ V11 - PROBLEM ÇÖZÜM VERSİYONU
================================================
Tüm problemler için çözüm içerir:
- Alt konu bazlı metin formatı
- Hedef kelime gösterim kuralları
- Halüsinasyon önleme
- Format tutarlılığı
"""

import json
import os

# ============================================================================
# ALT KONU KILAVUZLARI (Genişletilmiş - Format Bilgisi Dahil)
# ============================================================================

ALT_KONU_KILAVUZLARI = {
    "Ana Düşünce": {
        "kazanim": "Öğrenci bir metnin ana fikrini/düşüncesini belirleyebilir.",
        "aciklama": "Metnin tamamını kapsayan, en genel yargı. Diğer cümleler bunu destekler.",
        "metin_formati": "PARAGRAF (80-120 kelime, giriş-gelişme-sonuç yapısında)",
        "hedef_gosterim": "YOK - Tüm metin önemli",
        "soru_formati": "Bu parçanın ana düşüncesi aşağıdakilerden hangisidir?",
        "soru_kokleri": [
            "Bu parçanın ana düşüncesi aşağıdakilerden hangisidir?",
            "Bu parçada asıl anlatılmak istenen aşağıdakilerden hangisidir?",
            "Bu parçadan çıkarılabilecek en kapsamlı yargı hangisidir?",
        ],
        "celdirici_taktikleri": [
            "Yardımcı düşünce (kısmi doğru ama ana fikir değil)",
            "Metinde geçen ama ana fikri yansıtmayan detay",
            "Metnin bir paragrafına özgü fikir",
        ],
        "yasak": "Metin çok kısa olmasın. Ana düşünce net çıkarılabilmeli. UYDURMA KAVRAM KULLANMA!",
    },
    
    "Sebep-Sonuç": {
        "kazanim": "Öğrenci cümleler arası sebep-sonuç ilişkisini belirleyebilir.",
        "aciklama": "Bir olayın NEDENİ veya SONUCU sorulur.",
        "metin_formati": "PARAGRAF (60-100 kelime, neden-sonuç bağlantısı NET)",
        "hedef_gosterim": "YOK - İlişki metinde aranacak",
        "soru_formati": "Bu parçada belirtilen durumun nedeni/sonucu aşağıdakilerden hangisidir?",
        "soru_kokleri": [
            "Bu parçada belirtilen durumun nedeni aşağıdakilerden hangisidir?",
            "Bu parçaya göre ... durumunun sonucu nedir?",
            "Parçada hangi neden-sonuç ilişkisi vardır?",
        ],
        "celdirici_taktikleri": [
            "Metinde geçen ama neden-sonuç ilişkisi olmayan bilgi",
            "Sonuç gibi görünen ama aslında bağımsız yargı",
            "Nedeni değil, koşulu veren şık",
        ],
        "yasak": "Soru kökünde 'neden', 'sonuç' gibi kelimeler MUTLAKA olmalı. UYDURMA BİLGİ KULLANMA!",
    },
    
    "Fiilimsiler": {
        "kazanim": "Öğrenci fiilimsileri (isim-fiil, sıfat-fiil, zarf-fiil) tanıyabilir.",
        "aciklama": "Fiil kökünden türeyen ama isim, sıfat veya zarf gibi kullanılan sözcükler.",
        "metin_formati": "4 BAĞIMSIZ CÜMLE (I, II, III, IV ile numaralandırılmış)",
        "hedef_gosterim": "Her cümlede hedef fiilimsi TİRNAK içinde: \"koşan\", \"gelen\"",
        "soru_formati": "Numaralanmış cümlelerin hangisinde fiilimsi kullanılmamıştır?",
        "soru_kokleri": [
            "Numaralanmış cümlelerin hangisinde fiilimsi kullanılmamıştır?",
            "Aşağıdaki cümlelerin hangisinde sıfat-fiil vardır?",
            "Hangi cümlede zarf-fiil kullanılmıştır?",
        ],
        "celdirici_taktikleri": [
            "Gerçek fiil (kip eki almış) - fiilimsi değil",
            "Fiilden türemiş ama isim olan sözcük",
            "Benzer sesli ama farklı türde sözcük",
        ],
        "yasak": "Paragraf formatı KULLANMA! 4 ayrı cümle yaz. UYDURMA FİİLİMSİ KULLANMA!",
    },
    
    "Çok Anlamlılık": {
        "kazanim": "Öğrenci aynı sözcüğün farklı anlamlarda kullanımını ayırt edebilir.",
        "aciklama": "Bir sözcük farklı cümlelerde farklı anlamlarda kullanılır.",
        "metin_formati": "4 BAĞIMSIZ CÜMLE (I, II, III, IV ile numaralandırılmış)",
        "hedef_gosterim": "Hedef kelime her cümlede TİRNAK içinde: \"göz\", \"el\", \"baş\"",
        "soru_formati": "Numaralanmış cümlelerin hangisinde \"kelime\" farklı anlamda kullanılmıştır?",
        "soru_kokleri": [
            "Numaralanmış cümlelerin hangisinde \"...\" sözcüğü farklı anlamda kullanılmıştır?",
            "Altı çizili sözcük hangi cümlede mecaz anlamda kullanılmıştır?",
            "Hangi cümlede \"...\" sözcüğü gerçek anlamında kullanılmıştır?",
        ],
        "celdirici_taktikleri": [
            "Aynı anlam, farklı bağlam",
            "Yakın anlam ama tam olarak aynı değil",
            "Ses benzerliği olan ama farklı sözcük",
        ],
        "yasak": "Paragraf formatı KULLANMA! 4 ayrı kısa cümle yaz. Hedef kelime TİRNAK İÇİNDE olmalı!",
    },
    
    "Noktalama": {
        "kazanim": "Öğrenci noktalama işaretlerinin kullanım amaçlarını belirleyebilir.",
        "aciklama": "Virgül, nokta, soru işareti, ünlem vb. işaretlerin cümledeki işlevi.",
        "metin_formati": "4 BAĞIMSIZ CÜMLE (I, II, III, IV ile numaralandırılmış)",
        "hedef_gosterim": "Her cümlede noktalama işareti NET görünmeli",
        "soru_formati": "Aşağıdaki cümlelerin hangisinde noktalama yanlışı vardır?",
        "soru_kokleri": [
            "Aşağıdaki cümlelerin hangisinde noktalama yanlışı vardır?",
            "Bu parçada virgülün kullanım amacı aşağıdakilerden hangisidir?",
            "Hangi cümlede soru işareti doğru kullanılmıştır?",
        ],
        "celdirici_taktikleri": [
            "Farklı işaretin kullanım amacı",
            "Aynı işaretin farklı kullanımı",
            "Doğru görünen ama aslında yanlış kural",
        ],
        "yasak": "Kural açıklama değil, UYGULAMA sorusu olmalı! Paragraf KULLANMA!",
    },
    
    "Başlık Bulma": {
        "kazanim": "Öğrenci metnin içeriğine uygun başlık belirleyebilir.",
        "aciklama": "Başlık metnin ana fikrini özetlemeli, dikkat çekici olmalı.",
        "metin_formati": "PARAGRAF (80-120 kelime, tek konu etrafında)",
        "hedef_gosterim": "YOK - Başlık şıklarda sunulacak",
        "soru_formati": "Bu parçaya en uygun başlık aşağıdakilerden hangisidir?",
        "soru_kokleri": [
            "Bu parçaya en uygun başlık aşağıdakilerden hangisidir?",
            "Bu metnin başlığı aşağıdakilerden hangisi olabilir?",
        ],
        "celdirici_taktikleri": [
            "Çok genel başlık",
            "Sadece bir bölüme uygun başlık",
            "Metinde geçen ama konuyu yansıtmayan ifade",
        ],
        "yasak": "Başlık seçenekleri benzer yapıda olmalı. UYDURMA KAVRAM KULLANMA!",
    },
    
    "Anlatım Biçimi": {
        "kazanim": "Öğrenci metnin anlatım biçimini (öyküleme, betimleme, açıklama, tartışma) belirleyebilir.",
        "aciklama": "Öyküleme=olay anlatır, Betimleme=tasvir eder, Açıklama=bilgi verir, Tartışma=görüş savunur.",
        "metin_formati": "PARAGRAF (80-120 kelime, TEK anlatım biçiminde)",
        "hedef_gosterim": "YOK - Anlatım biçimi metinden çıkarılacak",
        "soru_formati": "Bu parçanın anlatım biçimi aşağıdakilerden hangisidir?",
        "soru_kokleri": [
            "Bu parçanın anlatım biçimi aşağıdakilerden hangisidir?",
            "Bu parçada hangi anlatım biçimi kullanılmıştır?",
        ],
        "celdirici_taktikleri": [
            "Küçük bir bölümden çıkarılan yanlış genelleme",
            "Anlatım biçimi karışımında baskın olanı kaçırmak",
        ],
        "yasak": "Metin TEK bir anlatım biçimini NET yansıtmalı. Karışık metin YAZMA!",
    },
    
    "Koşul": {
        "kazanim": "Öğrenci cümlede koşul anlamı taşıyan yapıları belirleyebilir.",
        "aciklama": "'-sa/-se' eki veya 'eğer', 'şayet' gibi bağlaçlar koşul bildirir.",
        "metin_formati": "4 BAĞIMSIZ CÜMLE (I, II, III, IV ile numaralandırılmış)",
        "hedef_gosterim": "Koşul yapısı cümlede NET görünmeli",
        "soru_formati": "Aşağıdaki cümlelerin hangisinde koşul anlamı vardır?",
        "soru_kokleri": [
            "Bu cümlede koşul anlamı hangi sözcükle sağlanmıştır?",
            "Aşağıdaki cümlelerin hangisinde koşul anlamı vardır?",
        ],
        "celdirici_taktikleri": [
            "Dilek-istek anlamı (koşul değil)",
            "Zaman anlamı (-ince, -dığında)",
            "Neden anlamı (-dığından)",
        ],
        "yasak": "Koşul ile dilek-istek karıştırılmamalı. Paragraf KULLANMA!",
    },
    
    "Öznel-Nesnel": {
        "kazanim": "Öğrenci öznel (kişisel) ve nesnel (objektif) yargıları ayırt edebilir.",
        "aciklama": "Öznel=duygu/düşünce içerir, Nesnel=kanıtlanabilir/ölçülebilir bilgi içerir.",
        "metin_formati": "4 BAĞIMSIZ CÜMLE (I, II, III, IV ile numaralandırılmış)",
        "hedef_gosterim": "YOK - Her cümle analiz edilecek",
        "soru_formati": "Aşağıdaki cümlelerin hangisi öznel yargı içermektedir?",
        "soru_kokleri": [
            "Aşağıdaki cümlelerin hangisi öznel yargı içermektedir?",
            "Bu parçadaki hangi cümle nesnel bir ifadedir?",
            "Hangi cümlede kişisel görüş bildirilmiştir?",
        ],
        "celdirici_taktikleri": [
            "Bilimsel görünen ama kişisel yargı içeren cümle",
            "Duygu içermeyen ama yine de öznel olan cümle",
        ],
        "yasak": "Öznel/nesnel kavramı TEK CÜMLEYE uygulanmalı. Paragraf KULLANMA!",
    },
    
    "Deyim": {
        "kazanim": "Öğrenci deyimlerin anlamlarını ve kullanımlarını belirleyebilir.",
        "aciklama": "Deyim: Gerçek anlamından farklı, kalıplaşmış söz öbeği.",
        "metin_formati": "4 BAĞIMSIZ CÜMLE (I, II, III, IV ile numaralandırılmış)",
        "hedef_gosterim": "Her cümlede deyim TİRNAK içinde: \"göz kulak olmak\", \"el vermek\"",
        "soru_formati": "Numaralanmış cümlelerin hangisinde deyim kullanılmamıştır?",
        "soru_kokleri": [
            "Numaralanmış cümlelerin hangisinde deyim kullanılmamıştır?",
            "Aşağıdaki cümlelerin hangisinde deyim kullanılmıştır?",
            "Hangi cümledeki deyim yanlış anlamda kullanılmıştır?",
        ],
        "celdirici_taktikleri": [
            "Deyimin gerçek anlamı",
            "Yakın anlamlı ama farklı deyim",
            "Atasözü (deyim değil)",
        ],
        "yasak": "Deyim METİNDE kullanılmalı. Paragraf KULLANMA! GERÇEK DEYİMLER kullan, UYDURMA!",
    },
    
    "Yazım Yanlışı": {
        "kazanim": "Öğrenci yazım kurallarına uygun/aykırı ifadeleri belirleyebilir.",
        "aciklama": "TDK yazım kuralları: Büyük harf, bitişik/ayrı yazım, kesme işareti vb.",
        "metin_formati": "4 BAĞIMSIZ CÜMLE (I, II, III, IV ile numaralandırılmış)",
        "hedef_gosterim": "Yazım yanlışı olan kelime cümlede NET görünmeli",
        "soru_formati": "Aşağıdaki cümlelerin hangisinde yazım yanlışı vardır?",
        "soru_kokleri": [
            "Aşağıdaki cümlelerin hangisinde yazım yanlışı vardır?",
            "Bu cümledeki yazım yanlışı nasıl düzeltilmelidir?",
            "Aşağıdakilerin hangisi doğru yazılmıştır?",
        ],
        "celdirici_taktikleri": [
            "Doğru görünen ama aslında yanlış yazım",
            "Konuşma dilinde doğru ama yazıda yanlış",
            "Sık karıştırılan yazım kuralı",
        ],
        "yasak": "Cümleler kısa ve net olmalı. Paragraf KULLANMA!",
    },
}

# ============================================================================
# STİL KILAVUZU (Güncellenmiş - Halüsinasyon Önleme)
# ============================================================================

STIL_KILAVUZU = """
## LGS TÜRKÇE SORU STİL KILAVUZU

### MUTLAK KURALLAR (İHLAL ETME!)
1. UYDURMA BİLGİ/KAVRAM KULLANMA - Sadece gerçek, bilinen bilgiler!
2. Aynı cümleyi TEKRAR etme, döngüye GİRME!
3. Ürettiğin soruyu KONTROL ET - şıklar metinle TUTARLI olmalı!
4. Türkçe dil bilgisi HATASIZ olmalı!

### Metin Kuralları
- Paragraf formatı: 80-120 kelime
- 4 cümle formatı: Her biri I, II, III, IV ile numaralı
- Dil: 8. sınıf seviyesi, anlaşılır

### Hedef Kelime Gösterimi
- Çok Anlamlılık: Kelime TİRNAK içinde → "göz", "el"
- Deyim: Deyim TİRNAK içinde → "göz kulak olmak"
- Fiilimsiler: Fiilimsi TİRNAK içinde → "koşan", "gelen"

### Şık Kuralları
- 4 şık (A, B, C, D)
- Benzer uzunluk ve biçim
- Mantıklı çeldiriciler
- Birbirine benzemeyen içerik
- UYDURMA şık KULLANMA!

### Kesin Yasaklar
- Numaralanmış paragraf (I. paragraf, II. paragraf) formatı
- "Hepsi" veya "Hiçbiri" şıkkı
- Çok uzun veya çok kısa şık
- Bariz yanlış çeldirici
- UYDURMA KAVRAM/TERİM
"""

# ============================================================================
# FARKINDALIK KONULARI
# ============================================================================

FARKINDALIK_KONULARI = [
    "Yapay Zekâ ve Teknoloji",
    "Çevre ve Doğa Koruma",
    "Sağlıklı Yaşam ve Beslenme",
    "Okuma Alışkanlığı",
    "Dijital Okuryazarlık",
    "Kültürel Miras ve Tarih",
    "Bilim ve Keşifler",
    "Sanat ve Estetik",
    "Spor ve Hareket",
    "Toplumsal Dayanışma",
    "İletişim Becerileri",
    "Zaman Yönetimi",
    "Eleştirel Düşünme",
    "Empati ve Duygusal Zekâ",
    "Girişimcilik",
    "Sürdürülebilir Yaşam",
    "Medya Okuryazarlığı",
    "Kariyer Planlaması",
    "Değerler Eğitimi",
    "Milli Bilinç",
]

# ============================================================================
# AKILLI RAG FONKSİYONLARI
# ============================================================================

def get_alt_konu_kilavuz(alt_konu: str) -> str:
    """Alt konu için kılavuz metni döndürür - GENİŞLETİLMİŞ FORMAT BİLGİSİ İLE."""
    kilavuz = ALT_KONU_KILAVUZLARI.get(alt_konu)
    if not kilavuz:
        return ""
    
    text = f"""
## {alt_konu.upper()} KILAVUZU

**Kazanım:** {kilavuz['kazanim']}

**Açıklama:** {kilavuz['aciklama']}

### ⚠️ METİN FORMATI (ÖNEMLİ!)
{kilavuz['metin_formati']}

### 🎯 HEDEF KELİME GÖSTERİMİ
{kilavuz['hedef_gosterim']}

### 📝 ÖNERİLEN SORU FORMATI
{kilavuz['soru_formati']}

**Örnek Soru Kökleri:**
{chr(10).join('- ' + k for k in kilavuz['soru_kokleri'])}

**Çeldirici Taktikleri:**
{chr(10).join('- ' + c for c in kilavuz['celdirici_taktikleri'])}

**⛔ YASAKLAR:** {kilavuz['yasak']}
"""
    return text.strip()

def get_rag_context(konu: str, alt_konu: str, farkindalik: str = None) -> str:
    """RAG context oluşturur: Kılavuz + Stil kuralları + Farkındalık teması."""
    
    parts = []
    
    # 1. Farkındalık teması (varsa)
    if farkindalik:
        parts.append(f"## METİN TEMASI\n**Farkındalık Konusu:** {farkindalik}\nMetin bu tema etrafında yazılmalı. GERÇEK bilgiler kullan!")
    
    # 2. Alt konu kılavuzu (GENİŞLETİLMİŞ)
    kilavuz = get_alt_konu_kilavuz(alt_konu)
    if kilavuz:
        parts.append(kilavuz)
    
    # 3. Stil kılavuzu
    parts.append(STIL_KILAVUZU)
    
    return "\n\n---\n\n".join(parts)

def build_rag_prompt(konu: str, alt_konu: str, farkindalik: str = None) -> str:
    """RAG destekli tam prompt oluşturur."""
    
    context = get_rag_context(konu, alt_konu, farkindalik)
    
    prompt = f"""Konu: {konu}
Alt Konu: {alt_konu}

{context}

---

Yukarıdaki kılavuza göre LGS Türkçe sorusu üret. 

MUTLAK KURALLAR:
1. METİN FORMATINA %100 UY! (Paragraf mı, 4 cümle mi?)
2. HEDEF KELİMEYİ gösterim kuralına göre işaretle!
3. UYDURMA kavram KULLANMA!
4. SADECE JSON döndür!

JSON:
{{"metin": "...", "soru": "...", "sik_a": "...", "sik_b": "...", "sik_c": "...", "sik_d": "...", "dogru_cevap": "A/B/C/D"}}"""
    
    return prompt


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("AKILLI RAG SİSTEMİ V11 - GENİŞLETİLMİŞ FORMAT")
    print("="*60)
    
    # Test
    for alt_konu in ["Çok Anlamlılık", "Ana Düşünce", "Deyim"]:
        print(f"\n{'='*60}")
        print(f"ALT KONU: {alt_konu}")
        print("="*60)
        prompt = build_rag_prompt("Paragraf", alt_konu)
        print(prompt[:800] + "...")
        print(f"\nPrompt uzunluğu: {len(prompt)} karakter")
