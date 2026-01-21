# 🎓 LGS Türkçe Soru Üretim Sistemi

AI destekli LGS Türkçe soruları üretme platformu.

## ✨ Özellikler

- 🤖 Groq API (Llama 3.3 70B) ile soru üretimi
- 🧠 RAG sistemi (92 high-quality örnek)
- 📝 PDF-style modern web arayüzü
- ✅ Kalite kontrolü ve validasyon
- 🎯 Alt konu bazlı özelleştirilmiş kurallar

## 🚀 Kurulum

```bash
# Dependencies
pip install -r requirements.txt

# .env dosyası oluştur
cp .env.example .env
# API keylerini ekle
```

## 📖 Kullanım

```bash
cd src
python web_app.py
```

Tarayıcıda: `http://localhost:5000`

## 🏗️ Mimari

- **Backend:** Flask
- **API:** Groq (Llama 3.3 70B)
- **RAG:** FAISS + Sentence Transformers
- **Frontend:** Modern HTML/CSS/JS

## 📊 Veri

- 92 kaliteli RAG örneği
- 1339 training örneği
- MEB referans soruları

## 🔧 Konfigürasyon

`.env` dosyasında:
```
GROQ_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

## 📁 Proje Yapısı

```
lgs_soru_tahmin_projesi/
├── src/                 # Ana uygulama
│   ├── web_app.py      # Flask server
│   ├── api_client.py   # API yönetimi
│   ├── question_generator.py
│   ├── rag_manager.py
│   └── templates/
├── data/               # Veri setleri
├── colab/              # Training notebooks
├── configs/            # Konfigürasyon
└── rag_docs/           # RAG dokümantasyonu
```

## 📝 Lisans

MIT License
