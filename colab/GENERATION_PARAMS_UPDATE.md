# Generation Parameters Update - Daha Çeşitli Şıklar İçin
# Colab notebook'ta generate_with_rag fonksiyonunu güncelle

## =========================================
## ŞU ANKİ PARAMETRELER (Muhtemelen):
## =========================================
"""
temperature=0.7,
top_p=0.9,
max_new_tokens=1200
"""

## =========================================
## YENİ PARAMETRELER (Daha Çeşitli):
## =========================================

# Colab'da generate_with_rag fonksiyonunu bul ve şu parametreleri kullan:

def generate_with_rag(
    konu,
    alt_konu,
    model,
    tokenizer,
    rag_system,
    max_new_tokens=1500,        # ✅ 1200 → 1500 (daha uzun şıklar)
    temperature=0.95,           # ✅ 0.7 → 0.95 (daha çeşitli)
    top_p=0.98,                 # ✅ 0.9 → 0.98 (daha geniş seçim)
    repetition_penalty=1.2      # ✅ YENİ! Pattern tekrarını önle
):
    """Generate with enhanced diversity parameters"""
    
    # ... existing code ...
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            repetition_penalty=repetition_penalty,  # ✅ EKLE!
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    # ... rest of code ...


## =========================================
## PARAMETRE AÇIKLAMALARI:
## =========================================

"""
temperature=0.95
- Daha yüksek = daha çeşitli/yaratıcı
- 0.7 → 0.95: Şıklarda daha fazla varyasyon

top_p=0.98  
- Nucleus sampling genişliği
- 0.9 → 0.98: Daha geniş token seçimi

repetition_penalty=1.2
- Pattern tekrarını cezalandır
- "X'in önemi" devamlı kullanımını azaltır

max_new_tokens=1500
- Daha uzun cevaplar
- Daha detaylı şıklar
"""

## =========================================
## BEKLENEN İYİLEŞME:
## =========================================

# ÖNCESİ (Generic):
example_before = {
    "sik_a": "Eğitimnin önemi",
    "sik_b": "Doğanin hayatımıza etkisi", 
    "sik_c": "Sağlıknin önemi",
    "sik_d": "Çevrenin önemi"
}

# SONRASI (Daha Spesifik):
example_after = {
    "sik_a": "Eğitimin bireysel gelişimdeki rolü",
    "sik_b": "Doğal kaynakların sürdürülebilir kullanımı",
    "sik_c": "Teknolojinin toplumsal değişime etkisi", 
    "sik_d": "Çevre bilincinin gelecek nesillere aktarımı"
}

## =========================================
## UYGULAMA ADIMLARI:
## =========================================

"""
1. Colab notebook'u aç
2. generate_with_rag fonksiyonunu bul
3. Parametreleri yukarıdaki gibi güncelle
4. Cell'i tekrar çalıştır
5. API server'ı restart et (ngrok cell'ini tekrar çalıştır)
6. Web app'ten test et

Alternatif (Hızlı):
- API endpoint'ine request'te parametre gönder
- Colab'da endpoint fonksiyonunu dinamik parametrelerle güncelle
"""

## =========================================
## GELIŞMIŞ: Dinamik Parametreler
## =========================================

# API Server'da /generate endpoint'ini güncelle:

@app.route('/generate', methods=['POST'])
def generate_endpoint():
    try:
        data = request.json
        konu = data.get("konu", "Paragraf")
        alt_konu = data.get("alt_konu", "Ana Düşünce")
        
        # ✅ Dinamik parametreler
        temperature = data.get("temperature", 0.95)
        top_p = data.get("top_p", 0.98) 
        
        result_json = generate_with_rag(
            konu, alt_konu,
            model, tokenizer, rag,
            temperature=temperature,  # ✅ Parametre geçir
            top_p=top_p,
            repetition_penalty=1.2
        )
        
        # ... rest ...
