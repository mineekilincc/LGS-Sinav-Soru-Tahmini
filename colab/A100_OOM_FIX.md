# A100 Memory Fix - OOM Hatası Çözümü

## 🚨 Problem
A100'de full precision + batch_size=4 = 40GB memory yetersiz!

## ✅ Çözüm

### ZORUNLU Değişiklikler:

#### 1. Model Loading'e Geri Dön (Section 4)
```python
# YANLIŞ (OOM veriyor):
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
    load_in_8bit=False,  # ❌ Bu hata veriyor
    device_map="auto",
    torch_dtype=torch.bfloat16
)

# DOĞRU (Çalışıyor):
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
    load_in_8bit=True,   # ✅ 8-bit geri getir
    device_map="auto",
    torch_dtype=torch.float16  # ✅ FP16 yeter
)
```

#### 2. Training Arguments - A100 için Optimize (Section 7)
```python
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    
    # Training parametreleri - A100 OPTIMIZED
    num_train_epochs=3,
    per_device_train_batch_size=2,      # ✅ 4→2 (OOM önleme)
    per_device_eval_batch_size=2,       # ✅ 4→2
    gradient_accumulation_steps=4,       # ✅ 2→4 (efektif batch=8)
    
    # Optimizer parametreleri
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    weight_decay=0.01,
    max_grad_norm=1.0,
    
    # Precision
    bf16=True,                          # ✅ A100 native BF16
    fp16=False,
    
    # Memory optimization
    gradient_checkpointing=True,        # ✅ EKLE! Memory tasarrufu
    
    # Logging ve kaydetme
    logging_steps=10,
    save_strategy="epoch",
    evaluation_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    
    # Diğer
    report_to="none",
    seed=42,
    dataloader_num_workers=2,           # ✅ 4→2 (memory için)
    remove_unused_columns=False
)
```

#### 3. LoRA Hazırlık - Gradient Checkpointing Ekle (Section 5)
```python
# Model'i LoRA için hazırla
model = prepare_model_for_kbit_training(model)

# ✅ EKLE: Gradient checkpointing aktif et
model.gradient_checkpointing_enable()

print("✅ Model LoRA için hazırlandı!")
print("✅ Gradient checkpointing aktif!")
```

## 📊 Yeni Konfigürasyon

| Parametre | Önceki | Yeni (OOM Fix) |
|-----------|--------|----------------|
| **load_in_8bit** | False | True ✅ |
| **torch_dtype** | bfloat16 | float16 ✅ |
| **batch_size** | 4 | 2 ✅ |
| **grad_accum** | 2 | 4 ✅ |
| **grad_checkpoint** | - | True ✅ |
| **workers** | 4 | 2 ✅ |

## ⏱️ Yeni Tahmini Süre

- **T4 GPU**: ~2-3 saat
- **A100 GPU**: ~45-60 dakika (hala T4'ten 2.5-3x hızlı!)

## 🔧 Uygulama Adımları

1. **Runtime'ı Restart Et**: Runtime → Restart Runtime
2. **Section 4'ü Düzelt**: `load_in_8bit=True`, `torch.float16`
3. **Section 5'e Ekle**: `model.gradient_checkpointing_enable()`
4. **Section 7'yi Düzelt**: batch_size=2, grad_accum=4, grad_checkpoint=True
5. **Tekrar Çalıştır**: Şimdi OOM olmayacak!

## 💡 Neden Bu Çalışıyor?

- **8-bit quantization**: Model 14B params → ~7GB (yarı yarıya düşer)
- **Gradient checkpointing**: Activation memory'yi trade-off eder (biraz yavaş ama çok az memory)
- **Batch size=2**: Her adımda daha az memory kullanır
- **Grad accum=4**: Efektif batch size hala 8 (aynı quality)

**Sonuç**: OOM yok, hala hızlı! 🚀
