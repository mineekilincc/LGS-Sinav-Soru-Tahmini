# -*- coding: utf-8 -*-
"""
LGS Soru Üretim Sistemi - Few-shot RAG ile Yeniden Tasarım
==========================================================
RAG'dan tam örnekler + Kalite kontrolü + Retry mekanizması
"""

import json
import os
import random
from typing import Dict, List, Any, Optional

# Proje modülleri
from question_templates import lgs_quality_check, get_stem_patterns_for_topic
from rag_manager import SimpleRAG

# Few-shot Prompt Şablonu
FEW_SHOT_PROMPT = """Sen MEB LGS Türkçe soru yazarısın. Aşağıdaki GERÇEK LGS soru örneklerini incele ve AYNI FORMATTA yeni bir soru üret.

## ÖRNEK SORULAR (Bu soruları referans al, kopyalama!)

{examples}

---

## ŞİMDİ SENİN ÜRETMEN GEREKEN SORU

**Konu:** {konu}
**Alt Konu:** {alt_konu}
**Zorluk:** {zorluk}
**Tema:** {tema}

## ZORUNLU KURALLAR:
1. Metin EN AZ 50 kelime olmalı (kısa metin KABUL EDİLMEZ!)
2. Metin 3-5 cümle içermeli, akıcı ve anlamlı olmalı
3. Soru kökü yukarıdaki örneklerdeki kalıplardan biri olmalı
4. 4 şık (A, B, C, D) birbirine yakın uzunlukta olmalı
5. Doğru cevap METİNDEN net olarak çıkarılabilmeli
6. Yanlış şıklar mantıklı görünmeli ama metinle çelişmeli

## ÇIKTI FORMATI (TAM BU FORMATTA YAZ!):
Metin: [En az 50 kelimelik paragraf]

Soru: [Soru kökü]

A) [Şık]
B) [Şık]
C) [Şık]
D) [Şık]

Doğru Cevap: [A/B/C/D]
"""

# Farkındalık konuları
AWARENESS_TOPICS = {
    "saglik": ["Teknoloji bağımlılığı", "Düzenli egzersiz", "Uyku düzeni"],
    "teknoloji": ["Yapay zekâ", "Dijital dönüşüm"],
    "cevre": ["Küresel ısınma", "Su tasarrufu", "Çevre kirliliği"],
    "toplum": ["Deprem bilinci", "Aile değerleri", "Geleneksel sanatlar"]
}


class LGSQuestionGenerator:
    """LGS Türkçe soru üretici - Few-shot RAG ile."""
    
    def __init__(self, data_path: str, awareness_ratio: float = 0.30):
        self.data_path = data_path
        self.awareness_ratio = awareness_ratio
        self.rag = None
        self.questions = None
        
    def initialize(self):
        """RAG ve verileri yükler."""
        # Veri setini yükle
        with open(self.data_path, 'r', encoding='utf-8') as f:
            self.questions = json.load(f)
        
        # İstatistikleri hesapla (şablon seçimi için gerekli)
        from question_templates import compute_stats
        self.stats = compute_stats(self.questions)
        print(f"✓ {len(self.questions)} soru yüklendi ve istatistikler hesaplandı")
        
        # RAG sistemini başlat
        cache_dir = os.path.dirname(self.data_path)
        self.rag = SimpleRAG()
        self.rag.initialize(cache_dir=cache_dir)
        self.rag.build_index(self.questions)
        print("✓ RAG sistemi hazır")
    
    def generate_prompt(
        self,
        konu: str = "Paragraf",
        alt_konu: str = "Ana Düşünce", 
        zorluk: str = "orta"
    ) -> Dict[str, Any]:
        """Gelişmiş şablon sistemiyle prompt oluşturur (RAG Destekli)."""
        
        # 2. Şablon taskı oluştur
        from question_templates import build_generation_task, build_prompt, format_reference_questions
        
        # override_topic ve override_alt_topic ile kullanıcının seçimini zorluyoruz
        task = build_generation_task(
            data=self.questions,
            stats=self.stats,
            target_year=2024,
            override_topic=konu,
            override_alt_topic=alt_konu
        )
        
        # Kullanıcının seçtiği zorluğu da ekle
        task["zorluk"] = zorluk
        
        # 1. RAG'dan referans soruları bul (Task oluştuktan sonra override ediyoruz)
        if self.rag:
            try:
                # Query: Konu + Alt Konu + Zorluk + Tema (varsa)
                rag_query = f"{konu} {alt_konu} {zorluk} {task.get('tema', '')}"
                print(f"🔍 RAG Aranıyor: {rag_query}")
                
                # Sıkı filtreleme: must_not_have ile problemli pattern'leri engelleyelim
                rag_results = self.rag.find_similar_strict(
                    query=rag_query,
                    k=4,
                    topic=konu,
                    subtopic=alt_konu,
                    must_not_have=["numaralanmış", "numaralandırılmış", "I., II., III."]  # Problemli pattern'ler
                )
                
                if rag_results:
                    rag_questions = [r["question"] for r in rag_results]
                    formatted_refs = format_reference_questions(rag_questions)
                    
                    # Şablondaki rastgele referansları EZ ve RAG'dan gelenleri koy
                    task["referans_sorular"] = formatted_refs
                    print(f"🔗 RAG'dan {len(rag_questions)} benzer soru prompt'a eklendi (sıkı filtreleme).")
                else:
                    print("⚠️ RAG sonuç döndürmedi, rastgele referanslar kullanılıyor.")
            except Exception as e:
                 print(f"⚠️ RAG hatası: {e}")

        
        # 3. Final promptu oluştur
        generated_prompt = build_prompt(task)
        
        # Eğer string ise (eski/basit yapı), dict'e çevir
        if isinstance(generated_prompt, str):
            final_prompt = {
                "system": "Sen MEB LGS Türkçe soru uzmanısın. LGS formatına ve şablona %100 sadık kal.",
                "user": generated_prompt
            }
        else:
            final_prompt = generated_prompt
        
        return {
            "prompt": final_prompt, # Artık dict {system:..., user:...}
            "konu": konu,
            "alt_konu": alt_konu,
            "zorluk": zorluk,
            "farkindalik_konusu": task.get("tema"),
            "example_count": len(rag_results) if 'rag_results' in locals() and rag_results else 0 
        }


def parse_llm_response(text: str) -> Dict[str, Any]:
    """LLM çıktısını parse eder (JSON ve Text desteği)."""
    result = {
        "metin": "",
        "soru_koku": "",
        "sik_a": "",
        "sik_b": "",
        "sik_c": "",
        "sik_d": "",
        "dogru_cevap": "",
        "raw": text,
        "success": False
    }
    
    if not text:
        return result
    
    # 1. Önce JSON parse etmeyi dene
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            data = json.loads(json_str)
            
            # Mapping
            result["metin"] = data.get("metin", data.get("text", ""))
            result["soru_koku"] = data.get("soru_koku", data.get("question", data.get("soru", "")))
            result["sik_a"] = data.get("sik_a", data.get("A", data.get("sikA", "")))
            result["sik_b"] = data.get("sik_b", data.get("B", data.get("sikB", "")))
            result["sik_c"] = data.get("sik_c", data.get("C", data.get("sikC", "")))
            result["sik_d"] = data.get("sik_d", data.get("D", data.get("sikD", "")))
            
            correct = data.get("dogru_cevap", data.get("answer", data.get("correct_answer", data.get("dogruCevap", ""))))
            if correct and isinstance(correct, str):
                result["dogru_cevap"] = correct.strip().upper()[-1]

            # Başarı kontrolü JSON için
            if (result["metin"] and result["soru_koku"] and 
                result["sik_a"] and result["sik_b"] and 
                result["sik_c"] and result["sik_d"] and
                result["dogru_cevap"]):
                result["success"] = True
                return result
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"⚠️ JSON parsing error: {e}")

    # 2. Text Parsing (Fallback) - Robust logic from api_client
    lines = text.strip().split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        
        if line.lower().startswith("metin:"):
            current_section = "metin"
            result["metin"] = line[6:].strip()
        elif line.lower().startswith("soru:"):
            current_section = "soru"
            result["soru_koku"] = line[5:].strip()
        elif line.startswith("A)") or line.startswith("a)"):
            result["sik_a"] = line[2:].strip()
            current_section = None
        elif line.startswith("B)") or line.startswith("b)"):
            result["sik_b"] = line[2:].strip()
        elif line.startswith("C)") or line.startswith("c)"):
            result["sik_c"] = line[2:].strip()
        elif line.startswith("D)") or line.startswith("d)"):
            result["sik_d"] = line[2:].strip()
        elif "doğru cevap" in line.lower() or "dogru cevap" in line.lower():
            # Robust logic for correct answer
            if ":" in line:
                candidate = line.split(":")[-1].strip().upper()
            else:
                candidate = line.upper()
            
            for char in candidate:
                if char in "ABCD":
                    result["dogru_cevap"] = char
                    break
        elif current_section == "metin" and line:
            result["metin"] += " " + line
        elif current_section == "soru" and line:
            result["soru_koku"] += " " + line
            
    # Başarı kontrolü
    if (result["metin"] and result["soru_koku"] and 
        result["sik_a"] and result["sik_b"] and 
        result["sik_c"] and result["sik_d"] and
        result["dogru_cevap"]):
        result["success"] = True
        
    return result


def validate_question(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Soru kalitesini kontrol eder (Gelişmiş lgs_quality_check kullanır)."""
    
    # 1. Parsing başarısızsa direkt dön
    if not parsed["success"]:
        return {"ok": False, "score": 0, "issues": ["Parsing başarısız (Eksik alanlar)"]}
    
    # 2. Seçenekleri sözlük formatına çevir
    options = {
        "A": parsed["sik_a"],
        "B": parsed["sik_b"],
        "C": parsed["sik_c"],
        "D": parsed["sik_d"]
    }
    
    # 3. Gelişmiş kontrolü çağır
    from question_templates import lgs_quality_check
    
    report = lgs_quality_check(
        metin=parsed["metin"],
        stem=parsed["soru_koku"],
        options=options,
        correct=parsed["dogru_cevap"]
    )
    
    return report


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    data_path = os.path.join(project_dir, "data", "merged_dataset_reclassified_fixed.json")
    
    print("=" * 60)
    print("LGS SORU ÜRETİM SİSTEMİ - FEW-SHOT RAG")
    print("=" * 60)
    
    generator = LGSQuestionGenerator(data_path)
    generator.initialize()
    
    result = generator.generate_prompt("Paragraf", "Ana Düşünce", "orta")
    
    print(f"\n📌 Örnek Sayısı: {result['example_count']}")
    print(f"📌 Farkındalık: {result['farkindalik_konusu'] or 'Yok'}")
    print("\n--- PROMPT (ilk 1000 karakter) ---")
    print(result["prompt"][:1000] + "...")
