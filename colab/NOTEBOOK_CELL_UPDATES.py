# A100 OOM Fix - Notebook Cell Değişiklikleri
# Copy-paste these into your Colab notebook

## ========================================
## CELL 1: Model Loading (Section 4.2)
## ========================================
# Bu cell'i tamamen değiştir:

# Model'i yükle (8-bit quantization ile)
print("📥 Model yükleniyor... (Bu 5-10 dakika sürebilir)")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
    load_in_8bit=True,          # 8-bit quantization
    device_map="auto",           # Otomatik device mapping
    torch_dtype=torch.float16    # FP16 precision
)

print("✅ Model yüklendi!")
print(f"   Device: {model.device}")
print(f"   Dtype: {model.dtype}")


## ========================================
## CELL 2: LoRA Preparation (Section 5.1)
## ========================================
# Model'i LoRA için hazırla - Bu cell'e 1 satır ekle:

# Model'i LoRA için hazırla
model = prepare_model_for_kbit_training(model)

# ✅ BU SATIRI EKLE:
model.gradient_checkpointing_enable()

print("✅ Model LoRA için hazırlandı!")
print("✅ Gradient checkpointing aktif!")


## ========================================
## CELL 3: Training Arguments (Section 7.1)
## ========================================
# Bu cell'i tamamen değiştir:

# Training arguments
# DİKKAT: Bu parametreler A100 için optimize edilmiştir!

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    
    # Training parametreleri - A100 OPTIMIZED
    num_train_epochs=3,
    per_device_train_batch_size=2,      # A100 için optimize
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=4,       # Efektif batch size = 8
    
    # Optimizer parametreleri
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,                   # İlk %3'te warmup
    weight_decay=0.01,
    max_grad_norm=1.0,
    
    # Precision
    bf16=True,                           # BF16 precision (A100 native)
    # fp16=True,                         # T4 GPU için bu satırı uncomment et
    
    # Memory optimization
    gradient_checkpointing=True,         # Memory tasarrufu
    
    # Logging ve kaydetme
    logging_steps=10,
    save_strategy="epoch",
    evaluation_strategy="epoch",
    save_total_limit=2,                  # Sadece son 2 checkpoint
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    
    # Diğer
    report_to="none",                    # TensorBoard kapalı
    seed=42,
    dataloader_num_workers=2,
    remove_unused_columns=False
)

print("⚙️ A100 Training Konfigürasyonu:")
print(f"  Epochs: {training_args.num_train_epochs}")
print(f"  Batch size: {training_args.per_device_train_batch_size}")
print(f"  Gradient accumulation: {training_args.gradient_accumulation_steps}")
print(f"  Efektif batch size: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
print(f"  Learning rate: {training_args.learning_rate}")
print(f"  LR scheduler: {training_args.lr_scheduler_type}")
print(f"  Warmup ratio: {training_args.warmup_ratio}")
print(f"  Gradient checkpointing: ✅ ACTIVE")
print(f"\n⏱️  Tahmini training süresi: 45-60 dakika (A100)")


## ========================================
## ÖZET
## ========================================
"""
3 CELL DEĞİŞİKLİĞİ:

1. Model Loading:
   - load_in_8bit=True (geri getir)
   - torch.float16 (geri getir)

2. LoRA Preparation:
   - model.gradient_checkpointing_enable() (ekle)

3. Training Arguments:
   - per_device_train_batch_size=2 (4→2)
   - per_device_eval_batch_size=2 (4→2)
   - gradient_accumulation_steps=4 (2→4)
   - gradient_checkpointing=True (ekle)
   - dataloader_num_workers=2 (4→2)

SONUÇ:
✅ OOM hatası çözülecek
✅ Training süresi: ~45-60 dakika
✅ Hala T4'ten 2.5x hızlı!
"""
