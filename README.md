# 🎓 LGS Türkçe Soru Tahmin ve Üretim Sistemi

## 📋 Proje Özeti

Bu proje, 2025 LGS Türkçe sınavı için:
- **RAG (Retrieval-Augmented Generation)** ile benzer soru bulma
- **Fine-tuned Llama-3** ile MEB formatında soru üretme
- **Farkındalık konuları** entegrasyonu (Yapay zeka, deprem bilinci, vb.)

## 🚀 Hızlı Başlangıç

### Kurulum
```bash
pip install -r requirements.txt
```

### CLI Kullanımı
```bash
# İnteraktif mod
python src/cli.py

# Toplu üretim (10 prompt)
python src/cli.py --batch 10 --output prompts.json
```

## 📁 Proje Yapısı

```
lgs_soru_tahmin_projesi/
├── data/
│   ├── merged_dataset.json      # 450 birleşik soru
│   ├── training_data.jsonl      # Fine-tuning verisi
│   └── rag_index.pkl            # RAG index cache
├── models/
│   └── lgs_turkish_lora/        # Fine-tuned model
├── src/
│   ├── question_generator.py    # Ana üretim modülü
│   ├── question_templates.py    # Şablon sistemi
│   ├── rag_manager.py           # RAG sistemi
│   ├── api_client.py            # API fallback
│   └── cli.py                   # Komut satırı
└── colab/
    └── lgs_fine_tuning.ipynb    # Fine-tuning notebook
```

## 🔧 Modüller

| Modül | Açıklama |
|-------|----------|
| `question_generator.py` | RAG + Şablon + Farkındalık entegrasyonu |
| `rag_manager.py` | Benzer soru bulma (cosine similarity) |
| `question_templates.py` | LGS analiz verileri ve kalıplar |
| `api_client.py` | Gemini/Groq API fallback |
| `cli.py` | Kullanıcı arayüzü |

## 📊 Eğitim Metrikleri

- **Veri:** 900 soru (450 orijinal + augmentation)
- **Model:** Llama-3-8B-Instruct + QLoRA
- **Final Loss:** 0.54
- **Eğitim Süresi:** ~56 dakika

## 🎯 Üretim Akışı

```
Kullanıcı Girişi (konu, zorluk)
         ↓
  Şablon Seçimi
         ↓
   RAG (3 referans)
         ↓
Farkındalık (%30 paragraf)
         ↓
  Fine-tuned LLM
         ↓
  Kalite Kontrolü
         ↓
    MEB Formatında Soru
```

## 📝 Lisans

Bu proje eğitim amaçlı geliştirilmiştir.
