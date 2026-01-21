# -*- coding: utf-8 -*-
"""
RAG V3 - 2 KATMANLI SİSTEM
===========================
Katman 1: RAG Docs (stratejik "nasıl" bilgisi)
Katman 2: Question Type Rules (kesin "ne" kuralları)
"""

import yaml
from pathlib import Path
from typing import Dict, Optional

class RAGSystemV3:
    """İki katmanlı RAG sistemi."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.rag_docs_dir = project_root / "rag_docs"
        self.rules_path = project_root / "configs" / "question_type_rules.yaml"
        
        # RAG docs yükle (cache için)
        self.rag_docs = {}
        self._load_rag_docs()
        
        # Rules yükle
        self.rules = {}
        self._load_rules()
    
    def _load_rag_docs(self):
        """RAG dokümanlarını yükle."""
        if not self.rag_docs_dir.exists():
            print(f"⚠️ RAG docs klasörü bulunamadı: {self.rag_docs_dir}")
            return
        
        for doc_file in self.rag_docs_dir.glob("*.md"):
            doc_name = doc_file.stem  # paragraf, cumlede_anlam vb.
            with  open(doc_file, 'r', encoding='utf-8') as f:
                self.rag_docs[doc_name] = f.read()
        
        print(f"✅ {len(self.rag_docs)} RAG doc yüklendi")
    
    def _load_rules(self):
        """Question Type Rules yükle."""
        if not self.rules_path.exists():
            print(f"⚠️ Rules dosyası bulunamadı: {self.rules_path}")
            return
        
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            self.rules = yaml.safe_load(f)
        
        print(f"✅ {len(self.rules)} soru tipi kuralı yüklendi")
    
    def get_rag_doc_for_topic(self, konu: str) -> Optional[str]:
        """Konu için uygun RAG doc'u getir."""
        
        # Eşleştirme
        konu_lower = konu.lower()
        if "paragraf" in konu_lower:
            return self.rag_docs.get("paragraf")
        elif "cümlede" in konu_lower or "cumlede" in konu_lower:
            return self.rag_docs.get("cumlede_anlam")
        elif "sözcükte" in konu_lower or "sozcukte" in konu_lower:
            return self.rag_docs.get("sozcukte_anlam")
        elif "dil bilgisi" in konu_lower:
            return self.rag_docs.get("dil_bilgisi")
        elif "yazım" in konu_lower or "noktalama" in konu_lower:
            return self.rag_docs.get("yazim_noktalama")
        
        return None
    
    def get_general_strategy(self) -> str:
        """Genel strateji dokümanını getir."""
        return self.rag_docs.get("lgs_tahmin_stratejisi", "")
    
    def get_rule_for_question_type(self, konu: str, alt_konu: str) -> Optional[Dict]:
        """Soru tipi için kesin kuralları getir."""
        
        # Rule key oluştur (örn: paragraf_ana_dusunce)
        konu_key = konu.lower().replace(" ", "_").replace("ü", "u").replace("ö", "o").replace("ç", "c").replace("ı", "i").replace("ş", "s").replace("ğ", "g")
        alt_konu_key = alt_konu.lower().replace(" ", "_").replace("ü", "u").replace("ö", "o").replace("ç", "c").replace("ı", "i").replace("ş", "s").replace("ğ", "g")
        
        rule_key = f"{konu_key}_{alt_konu_key}"
        
        # Kuralı bul
        for key, rule in self.rules.items():
            if key == rule_key:
                return rule
            # Alternatif: alt_konu eşleşmesi
            if rule.get("alt_konu", "").lower().replace(" ", "_") == alt_konu_key:
                return rule
        
        return None
    
    def build_full_prompt(self, konu: str, alt_konu: str, tema: Optional[str] = None) -> str:
        """Tam prompt oluştur: RAG Doc + Rules + Tema."""
        
        # 1. RAG Doc (Stratejik bilgi)
        rag_doc = self.get_rag_doc_for_topic(konu)
        
        # 2. Genel strateji
        general_strategy = self.get_general_strategy()
        
        # 3. Question Type Rules
        rule = self.get_rule_for_question_type(konu, alt_konu)
        
        # Default word counts
        min_words = 80
        max_words = 150
        
        if rule:
            min_words = rule.get('min_words', 80)
            max_words = rule.get('max_words', 150)
        
        # Prompt oluştur
        prompt = f"""Sen MEB LGS 8. sınıf Türkçe soru yazarısın.

## KONU BİLGİSİ
Konu: {konu}
Alt Konu: {alt_konu}
"""
        
        if tema:
            prompt += f"Tema: {tema}\n"
        
        # RAG Doc ekle
        if rag_doc:
            prompt += f"\n## STRATEJİK KILAVUZ\n{rag_doc}\n"
        
        # Rule ekle
        if rule:
            prompt += f"\n## KESİN KURALLAR\n"
            prompt += f"- Metin kelime sayısı: {min_words}-{max_words} kelime\n"
            
            if rule.get('numbered_sentences'):
                prompt += "- Metin formatı: Numaralı cümleler (I. II. III. IV.)\n"
            else:
                prompt += "- Metin formatı: Paragraf (numaralı cümle KULLANMA)\n"
            
            if rule.get('highlight_required'):
                highlight_fmt = rule.get('highlight_format', 'tırnak')
                prompt += f"- Hedef kelime vurgusu: {highlight_fmt} içinde göster (örn: \"göz\")\n"
            
            allowed_roots = rule.get('allowed_question_roots', [])
            if allowed_roots:
                prompt += f"- İzin verilen soru kökleri:\n"
                for root in allowed_roots:
                    prompt += f"  - {root}\n"
        else:
            # Rule bulunamadıysa basit kurallar
            prompt += f"\n## TEMEL KURALLAR\n"
            prompt += f"- Metin kelime sayısı: {min_words}-{max_words} kelime\n"
            prompt += "- Metin formatı: Paragraf\n"
        
        # Genel strateji ekle (önemli tuzaklar)
        if general_strategy:
            prompt += f"\n## GENEL ÇELDİRİCİ STRATEJİLERİ\n{general_strategy[:800]}...\n"  # İlk 800 karakter
        
        # JSON format talimatı
        prompt += f"""
## ÇIKTI FORMATI
SADECE aşağıdaki JSON formatında döndür:

{{"metin": "Metin buraya ({min_words}-{max_words} kelime)", "soru": "Soru metni", "sik_a": "A şıkkı", "sik_b": "B şıkkı", "sik_c": "C şıkkı", "sik_d": "D şıkkı", "dogru_cevap": "A"}}

SADECE JSON döndür, başka hiçbir şey yazma!
"""
        
        return prompt
    
    def build_simple_prompt_for_finetune(self, konu: str, alt_konu: str, tema: Optional[str] = None) -> str:
        """Fine-tune için basitleştirilmiş prompt (tüm stratejileri öğrenecek)."""
        
        rule = self.get_rule_for_question_type(konu, alt_konu)
        
        prompt = f"""Konu: {konu}
Alt Konu: {alt_konu}
"""
        
        if tema:
            prompt += f"Tema: {tema}\n"
        
        if rule:
            min_w = rule.get('min_words', 80)
            max_w = rule.get('max_words', 150)
            prompt += f"\nMetin {min_w}-{max_w} kelime olmalı."
            
            if rule.get('numbered_sentences'):
                prompt += " Numaralı cümleler kullan (I. II. III.)."
            else:
                prompt += " Paragraf şeklinde yaz."
        
        prompt += "\n\nBu kriterlere göre LGS Türkçe sorusu üret."
        
        return prompt


def test_rag_v3():
    """RAG V3 test."""
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent
    rag = RAGSystemV3(project_root)
    
    # Test 1: Paragraf - Ana Düşünce
    print("\n" + "="*60)
    print("TEST 1: Paragraf - Ana Düşünce")
    print("="*60)
    prompt = rag.build_full_prompt("Paragraf", "Ana Düşünce", tema="Teknoloji")
    print(prompt[:500])
    print("...")
    
    # Test 2: Sözcükte Anlam - Çok Anlamlılık
    print("\n" + "="*60)
    print("TEST 2: Sözcükte Anlam - Çok Anlamlılık")
    print("="*60)
    prompt = rag.build_full_prompt("Sözcükte Anlam", "Çok Anlamlılık", tema="Spor")
    print(prompt[:500])
    print("...")
    
    # Test 3: Basitleştirilmiş prompt
    print("\n" + "="*60)
    print("TEST 3: Basitleştirilmiş Prompt (Fine-tune için)")
    print("="*60)
    prompt = rag.build_simple_prompt_for_finetune("Cümlede Anlam", "Deyim", tema="Sağlık")
    print(prompt)


if __name__ == "__main__":
    test_rag_v3()
