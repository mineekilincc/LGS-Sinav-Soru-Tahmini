# 🚀 L4 Production Inference - Quick Start Guide

## 📋 Hazırlık (5 dakika)

### 1. Drive'a RAG Dosyalarını Yükle

**Klasör oluştur:**
```
LGS_Training/
└── rag_system/
    ├── rag_docs/
    ├── configs/
    └── rag_v3.py
```

**Yüklenecek dosyalar:**

#### `rag_docs/` klasörüne (6 dosya):
- `paragraf.md`
- `cumlede_anlam.md`
- `sozcukte_anlam.md`
- `dil_bilgisi.md`
- `yazim_noktalama.md`
- `lgs_tahmin_stratejisi.md`

#### `configs/` klasörüne (1 dosya):
- `question_type_rules.yaml`

#### Ana klasöre (1 dosya):
- `rag_v3.py`

**Kaynak:** Local `c:\Users\Yusuf Uygur\lgs_soru_tahmin_projesi\`

---

## 🎯 Kullanım (3 dakika setup + ready!)

### 1. Colab'da Aç
- `Qwen_LGS_Production_RAG.ipynb` dosyasını Colab'a yükle
- Runtime → Change runtime type → **L4 GPU** seç

### 2. Çalıştır
- Run all cells (3-5 dakika)
- Model yüklenecek
- RAG V3 entegre edilecek
- Production API hazır!

### 3. Kullan

**Single generation:**
```python
question = generator.generate("Paragraf", "Ana Düşünce")
print(question)
```

**Batch generation:**
```python
requests = [
    ("Paragraf", "Ana Düşünce"),
    ("Cümlede Anlam", "Sebep-Sonuç"),
    ("Sözcükte Anlam", "Çok Anlamlılık"),
]
results = generator.batch_generate(requests)
```

---

## 📊 L4 GPU Özellikleri

| Özellik | L4 GPU | A100 GPU | T4 GPU |
|---------|--------|----------|--------|
| **VRAM** | 24GB | 40GB | 16GB |
| **Maliyet** | $$ | $$$$ | $ |
| **Inference Hızı** | Fast | Fastest | Moderate |
| **Bizim İçin** | ✅ PERFECT | Overkill | Yavaş |

### L4 Advantages:
- ✅ **İdeal inference GPU**
- ✅ **24GB VRAM** (14B model + RAG için yeterli)
- ✅ **FP16 native** (hızlı)
- ✅ **Cost-effective** (A100'ün yarısı)
- ✅ **Tensor Cores** (optimized)

---

## 🎯 Notebook Özellikleri

### Sections:
1. **Setup** - Mount Drive, install deps (1 min)
2. **Config** - Paths setup (10 sec)
3. **Load Model** - Fine-tuned model from Drive (3-4 min)
4. **Load RAG** - RAG V3 system (10 sec)
5. **Functions** - Production utilities (instant)
6. **API Class** - Enhanced generator (instant)
7. **Quick Test** - 2 test generations (30 sec)
8. **Comprehensive Test** - 10 topics (3 min)
9. **Save Results** - Export to Drive (5 sec)
10. **Examples** - Usage patterns (on demand)

### Total Time:
- **First run**: ~5 minutes
- **Subsequent**: Instant (model cached)

---

## 💡 Optimization Features

### L4-Specific:
- ✅ FP16 precision (native on L4)
- ✅ Optimal batch size (inference)
- ✅ Low CPU mem usage
- ✅ Device auto-mapping

### RAG Integration:
- ✅ Enhanced system prompts
- ✅ Strategic knowledge injection
- ✅ Strict rule compliance
- ✅ Automatic validation

### Production Features:
- ✅ Retry logic (3 attempts)
- ✅ Error handling
- ✅ Statistics tracking
- ✅ Batch processing
- ✅ Result export

---

## 📈 Expected Performance

### Generation Speed (L4):
- **Single question**: 10-15 seconds
- **Batch (10 questions)**: ~2-3 minutes
- **vs A100**: Slightly slower (acceptable)
- **vs T4**: Much faster!

### Quality Metrics:
- **Format success**: >95%
- **Rule compliance**: >90%
- **Word count accuracy**: >95%
- **JSON validity**: 100%

---

## 🔧 Troubleshooting

### OOM Error?
- L4'te olmaz (24GB yeterli)
- Ama olursa: runtime restart → L4 seçili mi kontrol et

### RAG Load Error?
- Drive path'i kontrol et
- `rag_system/` klasörü var mı?
- 8 dosya yüklü mü?

### Slow Generation?
- L4 GPU seçili mi kontrol et
- CPU'da çalışıyor olabilir
- Runtime → Change runtime type → L4

### JSON Parse Error?
- Retry logic var (auto-retry)
- 3 denemede düzelir genelde
- Persist ederse: temp/top_p ayarla

---

## 💾 File Structure Check

**Drive'da olması gerekenler:**

```
LGS_Training/
├── v13_data/
│   ├── train.jsonl ✅
│   └── val.jsonl ✅
├── v13_models/
│   └── qwen_v13_final/
│       └── final_model/ ✅
│           ├── adapter_config.json
│           ├── adapter_model.bin
│           ├── ...
└── rag_system/ ⚠️ EKLENECEK
    ├── rag_docs/ (6 files)
    │   ├── paragraf.md
    │   ├── cumlede_anlam.md
    │   ├── sozcukte_anlam.md
    │   ├── dil_bilgisi.md
    │   ├── yazim_noktalama.md
    │   └── lgs_tahmin_stratejisi.md
    ├── configs/ (1 file)
    │   └── question_type_rules.yaml
    └── rag_v3.py
```

---

## ✅ Pre-Flight Checklist

- [ ] RAG files uploaded to Drive (8 files)
- [ ] Notebook uploaded to Colab
- [ ] Runtime set to L4 GPU
- [ ] Drive paths configured correctly
- [ ] Run all cells
- [ ] Model loaded successfully
- [ ] RAG V3 loaded successfully
- [ ] Quick test passed
- [ ] Ready for production! 🚀

---

## 🎊 Benefits Summary

### vs Training Notebook:
- ✅ **No training** → Ucuz!
- ✅ **Just inference** → Hızlı!
- ✅ **L4 instead of A100** → $$ tasarruf
- ✅ **Can run 24/7** → Sürekli kullan

### vs Local:
- ✅ **GPU access** → Çok hızlı
- ✅ **No local GPU needed** → Herkes kullanabilir
- ✅ **Cloud storage** → Drive entegre
- ✅ **Reproducible** → Hep aynı sonuç

### RAG V3 Benefits:
- ✅ **Better compliance** → Rules takip eder
- ✅ **Higher quality** → Strategic knowledge
- ✅ **Consistent output** → Predictable
- ✅ **Professional** → Production-ready

---

## 🚀 Next Steps

1. **Upload RAG files** (5 min)
2. **Run notebook** (3-5 min)
3. **Test generation** (1 min)
4. **Start using!** 🎉

**Total:** ~10 minutes to production-ready system!

---

**Version**: Production V13  
**GPU**: L4 (24GB)  
**Model**: Qwen 2.5 14B Fine-tuned  
**RAG**: V3 (2-layer system)
