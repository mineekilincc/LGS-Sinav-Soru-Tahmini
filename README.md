# LGS Türkçe Soru Üretim Sistemi

Bu proje, yapay zeka kullanarak LGS Türkçe sınavı için otomatik soru üretir.

## Proje Nedir?

Sistem, kullanıcının seçtiği konu ve alt konuya göre MEB formatında LGS Türkçe soruları üretir. Üretilen sorular:
- Gerçek LGS sorularına benzer kalitede
- Paragraf, cümlede anlam, sözcükte anlam, dil bilgisi ve yazım kuralları konularını kapsar
- Farkındalık konularını (yapay zeka, çevre, deprem bilinci vb.) içerir
- JSON formatında döner ve web arayüzünde gösterilir

## Nasıl Çalışır?

### 1. RAG Sistemi
- 92 yüksek kaliteli LGS sorusu veri tabanında saklanır
- Kullanıcı bir konu seçtiğinde, benzer sorular bulunur
- Bu sorular örnek olarak AI modeline verilir

### 2. Soru Üretimi
Sistem iki yöntemle soru üretir:

**Groq API (Varsayılan):**
- Llama 3.3 70B modeli kullanılır
- RAG örnekleri + konu kuralları ile prompt oluşturulur
- 2-3 saniyede soru üretilir

**Colab Fine-tuned Model (Opsiyonel):**
- Qwen 2.5 32B modeli 1339 örnekle eğitilmiştir
- QLoRA ile fine-tuning yapılmıştır
- Cloudflare Tunnel ile API olarak sunulur

### 3. Farkındalık Konuları
Paragraf sorularının %40'ında otomatik olarak güncel konular eklenir:
- Yapay zeka ve günlük yaşam
- Küresel ısınma ve iklim değişikliği
- Dijital okuryazarlık ve internet güvenliği
- Deprem bilinci ve afet hazırlığı
- Yenilenebilir enerji kaynakları
- (Toplam 12 konu)

### 4. Kalite Kontrolü
Her üretilen soru şu kriterlere göre değerlendirilir:
- Template kalite skoru (JSON formatı, alan kontrolü)
- Konu uyumu skoru (alt konu kurallarına uygunluk)
- Toplam skor 80/100'ün altındaysa soru reddedilir ve yeniden üretilir

## Kurulum

### Gereksinimler
```bash
pip install -r requirements.txt
```

### API Anahtarları
`.env` dosyası oluşturun:
```
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key (opsiyonel)
COLAB_API_URL=your_cloudflare_tunnel_url (opsiyonel)
```

## Kullanım

### Web Arayüzü
```bash
cd src
python web_app.py
```
Tarayıcıda `http://localhost:5000` adresine gidin.

### API Kullanımı
```python
from api_client import QuestionGeneratorAPI

api = QuestionGeneratorAPI(gemini_key, groq_key)
result = api.generate({
    "user": "Konu: Paragraf\nAlt Konu: Ana Düşünce"
})
```

## Model Eğitimi (Colab)

### 1. Veri Hazırlama
- `data/lgs_finetune_data_v10_simple.jsonl` dosyası kullanılır
- 1339 eğitim örneği içerir
- Her örnek: kullanıcı promptu + model cevabı (JSON)

### 2. Fine-tuning
`colab/lgs_finetune_v10_simple.ipynb` notebook'unu çalıştırın:

**Model:** Qwen 2.5 32B Instruct (4-bit)
**Yöntem:** QLoRA (r=32, alpha=64)
**Eğitim:** 3 epoch, learning rate 5e-5
**Süre:** 6-8 saat (A100 GPU)

### 3. Model Kaydetme
Eğitim sonunda model Google Drive'a kaydedilir:
```
/content/drive/MyDrive/lgs_soru_tahmin_projesi/models/lgs_qwen_32b_v10
```

## Colab API Kurulumu

### 1. Model Yükleme
`colab/run_model_api_v10.ipynb` notebook'unu çalıştırın.

### 2. Cloudflare Tunnel
```python
from pycloudflared import try_cloudflare
tunnel_url = try_cloudflare(port=5000)
print(f"API URL: {tunnel_url}")
```

### 3. Local .env Güncelleme
Tunnel URL'ini `.env` dosyasına ekleyin:
```
COLAB_API_URL=https://xxx.trycloudflare.com
```

## Proje Yapısı

```
lgs_soru_tahmin_projesi/
├── src/
│   ├── web_app.py              # Flask web server
│   ├── api_client.py           # API yönetimi (Groq/Colab)
│   ├── question_generator.py   # Soru üretim logic
│   ├── rag_manager.py          # RAG sistemi
│   ├── question_templates.py   # Şablon ve validasyon
│   └── templates/index.html    # Web arayüzü
├── data/
│   ├── guncel_yapilandirilmiş_veri_seti_v3_clean.json  # RAG (92 soru)
│   ├── lgs_finetune_data_v10_simple.jsonl              # Training data
│   └── rag_index_v10.pkl                               # RAG index
├── colab/
│   ├── lgs_finetune_v10_simple.ipynb    # Fine-tuning notebook
│   └── run_model_api_v10.ipynb          # API server notebook
├── configs/
│   └── question_type_rules.yaml         # Alt konu kuralları
└── rag_docs/                            # RAG stratejik bilgi
```

## Teknik Detaylar

### RAG (Retrieval-Augmented Generation)
- **Embedding Model:** sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- **Index:** FAISS (L2 distance)
- **Search:** Konu + alt konu + zorluk ile benzer 4 soru bulunur

### Prompt Enhancement
Her API çağrısında prompt şu katmanlarla zenginleştirilir:
1. Few-shot examples (RAG'dan 4 soru)
2. Stratejik bilgi (konu bazlı ipuçları)
3. Alt konu kuralları (soru formatı, yasak kelimeler)
4. Farkındalık konusu (%40 şans)
5. Ultra-strict uyarılar (yabancı kelime yasağı, metin uzunluğu vb.)

### API Öncelik Sırası
1. Groq API (hızlı, kaliteli)
2. Gemini API (yedek)
3. Colab API (fine-tuned model, opsiyonel)

## Performans

- **Ortalama yanıt süresi:** 2-3 saniye
- **Başarı oranı:** %85 (ilk denemede)
- **Ortalama kalite skoru:** 90/100
- **RAG arama süresi:** <100ms

## Lisans

MIT License
