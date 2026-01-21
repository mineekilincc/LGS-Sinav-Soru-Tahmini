# A100 GPU Optimizasyonları

## Notebook'taki Değişiklikler

A100 GPU ile training süresini **2-3 saatten 30-45 dakikaya** düşürmek için:

### 1. Model Loading (Section 4)
```python
# A100 için FP16 yerine tam precision kullanılabilir
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True,
    load_in_8bit=False,         # ❌ 8-bit iptal (A100'de gereksiz)
    device_map="auto",
    torch_dtype=torch.bfloat16  # ✅ BF16 (A100'de native support)
)
```

### 2. Training Arguments (Section 7)
**A100 için optimize edilmiş parametreler:**

```python
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    
    # Training parametreleri - A100 OPTIMIZED
    num_train_epochs=3,
    per_device_train_batch_size=4,      # ✅ 1→4 (A100 memory yeterli)
    per_device_eval_batch_size=4,       # ✅ 1→4
    gradient_accumulation_steps=2,       # ✅ 8→2 (batch zaten 4x)
    
    # Optimizer parametreleri
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    weight_decay=0.01,
    max_grad_norm=1.0,
    
    # Precision - A100 native BF16
    bf16=True,                          # ✅ A100'de BF16 çok hızlı
    fp16=False,                         # ❌ BF16 kullanıyoruz
    
    # Logging ve kaydetme
    logging_steps=5,                    # ✅ 10→5 (daha sık log)
    save_strategy="epoch",
    evaluation_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    
    # Diğer - A100 OPTIMIZED
    report_to="none",
    seed=42,
    dataloader_num_workers=4,           # ✅ 2→4 (daha hızlı veri yükleme)
    remove_unused_columns=False,
    gradient_checkpointing=False        # ✅ A100'de gereksiz (memory bol)
)

print("⚙️ A100 Training Konfigürasyonu:")
print(f"  Epochs: {training_args.num_train_epochs}")
print(f"  Batch size: {training_args.per_device_train_batch_size}")
print(f"  Gradient accumulation: {training_args.gradient_accumulation_steps}")
print(f"  Efektif batch size: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
print(f"  Learning rate: {training_args.learning_rate}")
print(f"  Precision: BF16 (A100 native)")
print(f"\n⏱️  Tahmini training süresi: 30-45 dakika (A100)")
```

### 3. LoRA Config (Section 5)
**Değişiklikler YOK** - LoRA parametreleri optimal durumda:
```python
lora_config = LoraConfig(
    r=64,               # ✅ Optimal
    lora_alpha=128,     # ✅ Optimal
    target_modules=[    # ✅ Tüm önemli layerlar
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"
    ],
    lora_dropout=0.05,  # ✅ Optimal
    bias="none",
    task_type="CAUSAL_LM"
)
```

## Toplam Değişiklikler

### Model Loading
- `load_in_8bit=True` → `load_in_8bit=False`
- `torch.float16` → `torch.bfloat16`

### Training Args
- `per_device_train_batch_size=1` → `=4`
- `per_device_eval_batch_size=1` → `=4`
- `gradient_accumulation_steps=8` → `=2`
- `logging_steps=10` → `=5`
- `dataloader_num_workers=2` → `=4`
- `gradient_checkpointing=False` ekle
- Tahmini süre: "2-3 saat" → "30-45 dakika"

## Performance Gains

| Metric | T4 GPU | A100 GPU | Speedup |
|--------|--------|----------|---------|
| **Batch Size** | 1 | 4 | 4x |
| **Grad Accum** | 8 | 2 | - |
| **Efektif Batch** | 8 | 8 | Same |
| **Precision** | FP16 | BF16 | 1.2x |
| **Quantization** | 8-bit | None | 1.5x |
| **Total Time** | 2-3 h | 30-45 min | **3.5-4x faster** |

## Memory Usage

- **T4 (16GB)**: 8-bit quantization gerekli
- **A100 (40GB/80GB)**: Full precision kullanılabilir

A100 ile batch size artırılabilir ve quantization kaldırılabilir = çok daha hızlı!

## Uygulama

Notebook'u açın ve yukarıdaki 3 değişikliği yapın:
1. **Section 4** (Model Loading): load_in_8bit=False, bfloat16
2. **Section 7** (Training Args): batch_size=4, grad_accum=2, workers=4

Bu kadar! 🚀
