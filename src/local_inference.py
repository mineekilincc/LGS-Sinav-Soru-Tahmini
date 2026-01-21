# -*- coding: utf-8 -*-
"""
LGS Fine-Tuned Model - Yerel Inference
======================================
Eğitilmiş Llama-3 modelini yükleyip soru üretir.
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
from typing import Dict, Any, Optional

class LocalLGSModel:
    """Fine-tuned Llama-3 modelini yükler ve inference yapar."""
    
    def __init__(
        self,
        adapter_path: str = "models/lgs_turkish_lora",
        base_model: str = "unsloth/llama-3-8b-Instruct-bnb-4bit",
        device: str = "auto"
    ):
        self.adapter_path = adapter_path
        self.base_model = base_model
        self.device = device
        self.model = None
        self.tokenizer = None
        
    def load_model(self):
        """Modeli ve tokenizer'ı yükler."""
        print(f"🔄 Base model yükleniyor: {self.base_model}")
        
        # GPU kontrolü
        has_cuda = torch.cuda.is_available()
        if has_cuda:
            print(f"✅ CUDA GPU bulundu: {torch.cuda.get_device_name(0)}")
        else:
            print("⚠️ GPU bulunamadı - CPU modunda çalışılacak (yavaş olabilir)")
        
        # 4-bit quantization config (sadece GPU varsa)
        if has_cuda:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
            device_map_arg = self.device
        else:
            # CPU modunda quantization kullanma
            bnb_config = None
            device_map_arg = "cpu"
        
        # Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model,
            trust_remote_code=True
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "right"
        
        # Base model
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                self.base_model,
                quantization_config=bnb_config,
                device_map=device_map_arg,
                trust_remote_code=True,
                torch_dtype=torch.float16 if has_cuda else torch.float32
            )
        except Exception as e:
            print(f"⚠️ Quantized model yüklenemedi: {e}")
            print("🔄 Fallback: Normal model yükleniyor...")
            # Fallback: quantization olmadan yükle
            self.model = AutoModelForCausalLM.from_pretrained(
                self.base_model.replace("-bnb-4bit", ""),  # Quantized olmayan versiyonu dene
                device_map="cpu",
                trust_remote_code=True,
                torch_dtype=torch.float32
            )
        
        print(f"✅ Base model yüklendi")
        
        # Adapter'ı yükle
        if os.path.exists(self.adapter_path):
            print(f"🔄 Adapter yükleniyor: {self.adapter_path}")
            self.model = PeftModel.from_pretrained(
                self.model,
                self.adapter_path,
                is_trainable=False
            )
            print("✅ Fine-tuned adapter yüklendi")
        else:
            print(f"⚠️ Adapter bulunamadı: {self.adapter_path}")
            print("Base model kullanılacak (fine-tune olmadan)")
        
        self.model.eval()
        print("✅ Model inference modunda hazır")
    
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 0.9,
        do_sample: bool = True
    ) -> str:
        """Prompt'tan metin üretir."""
        
        if self.model is None:
            raise RuntimeError("Model henüz yüklenmedi. Önce load_model() çağırın.")
        
        # Llama-3 Instruct formatı
        formatted_prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

Sen MEB LGS Türkçe soru yazma konusunda uzmanlaşmış bir yapay zeka asistanısın.<|eot_id|><|start_header_id|>user<|end_header_id|>

{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
        
        # Tokenize
        inputs = self.tokenizer(
            formatted_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        ).to(self.model.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode
        generated_text = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )
        
        return generated_text.strip()


# Global instance (lazy loading)
_model_instance: Optional[LocalLGSModel] = None

def get_model() -> LocalLGSModel:
    """Singleton pattern ile model instance döndürür."""
    global _model_instance
    if _model_instance is None:
        _model_instance = LocalLGSModel()
        _model_instance.load_model()
    return _model_instance


if __name__ == "__main__":
    # Test
    print("=" * 60)
    print("YEREL MODEL TEST")
    print("=" * 60)
    
    model = get_model()
    
    test_prompt = """Paragraf konusunda, Ana Düşünce alt konusunda, orta zorlukta bir LGS sorusu üret.

Metin: Bilim ve teknoloji hakkında 50-60 kelimelik bir paragraf yaz.

Soru: Bu metinde anlatılmak istenen aşağıdakilerden hangisidir?

A) [Seçenek]
B) [Seçenek]
C) [Seçenek]
D) [Seçenek]

Doğru Cevap: [A/B/C/D]"""
    
    print("\n📝 Test Promptu:")
    print(test_prompt[:200] + "...")
    
    print("\n🤖 Model Çıktısı:")
    result = model.generate(test_prompt, max_new_tokens=512)
    print(result)
