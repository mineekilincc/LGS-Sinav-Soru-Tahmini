# -*- coding: utf-8 -*-
"""
RAG Sistemi V2 - SADELEŞTİRİLMİŞ
================================
- 1818 eğitim sorusu ile index
- Şablon sistemi bypass
- Doğrudan basit prompt
"""

import json
import os
import pickle
from typing import List, Dict, Any, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False
    print("⚠ SentenceTransformers yüklü değil.")


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """İki vektör arasındaki cosine similarity."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)


class SimpleRAGv2:
    """Sadeleştirilmiş RAG sistemi - V8 eğitim verisiyle uyumlu."""
    
    def __init__(self):
        self.model = None
        self.embeddings = None
        self.questions = None
        self.index_path = None
        
    def initialize(self, cache_dir: str = "./data"):
        """Model başlat."""
        if not SBERT_AVAILABLE:
            raise ImportError("SentenceTransformers gerekli")
        
        print("🔄 Embedding model yükleniyor...")
        self.model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.index_path = os.path.join(cache_dir, "rag_index_v2.pkl")
        print("✓ Model hazır.")
        
    def _create_embedding_text(self, question: Dict[str, Any]) -> str:
        """Soru kaydından embedding için metin oluşturur."""
        # V8 formatından bilgi çıkar
        user = question.get("user", "")
        
        parts = []
        for line in user.split("\n"):
            if line.startswith("Konu:"):
                parts.append(line)
            elif line.startswith("Alt Konu:"):
                parts.append(line)
            elif line.startswith("Zorluk:"):
                parts.append(line)
        
        # Assistant'tan soru kökü
        try:
            assistant = question.get("assistant", "{}")
            data = json.loads(assistant)
            soru = data.get("soru", "")
            if soru:
                parts.append(f"Soru: {soru[:150]}")
        except:
            pass
        
        return " ".join(parts)
    
    def build_index(self, data_path: str, force: bool = False):
        """JSONL dosyasından index oluşturur."""
        if not self.model:
            raise RuntimeError("Önce initialize() çağırın.")
        
        # Cache kontrolü
        if not force and os.path.exists(self.index_path):
            print("📂 Mevcut index yükleniyor...")
            self.load_index()
            return
        
        # Veriyi yükle
        print(f"📂 Veri yükleniyor: {data_path}")
        questions = []
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    questions.append(json.loads(line.strip()))
                except:
                    pass
        
        print(f"✅ {len(questions)} soru yüklendi")
        
        # Embedding oluştur
        print("🔄 Embeddingler oluşturuluyor...")
        self.questions = questions
        texts = [self._create_embedding_text(q) for q in questions]
        self.embeddings = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        
        # Kaydet
        self.save_index()
        print(f"✅ Index hazır: {len(self.questions)} soru")
    
    def save_index(self):
        """Index'i diske kaydeder."""
        data = {
            "embeddings": self.embeddings,
            "questions": self.questions,
        }
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        with open(self.index_path, 'wb') as f:
            pickle.dump(data, f)
        print(f"💾 Index kaydedildi: {self.index_path}")
    
    def load_index(self):
        """Index'i diskten yükler."""
        with open(self.index_path, 'rb') as f:
            data = pickle.load(f)
        self.embeddings = data["embeddings"]
        self.questions = data["questions"]
        print(f"✅ Index yüklendi: {len(self.questions)} soru")
    
    def find_similar(
        self, 
        konu: str,
        alt_konu: str,
        zorluk: str = "orta",
        k: int = 2
    ) -> List[Dict[str, Any]]:
        """Benzer soruları bulur."""
        if self.embeddings is None or not self.model:
            return []
        
        # Query oluştur
        query = f"Konu: {konu} Alt Konu: {alt_konu} Zorluk: {zorluk}"
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
        
        # Similarity hesapla
        similarities = []
        for i, emb in enumerate(self.embeddings):
            sim = cosine_similarity(query_embedding, emb)
            
            # Alt konu eşleşmesi bonus
            user = self.questions[i].get("user", "")
            if f"Alt Konu: {alt_konu}" in user:
                sim *= 1.5  # %50 bonus
            
            similarities.append((i, sim))
        
        # Top-k
        similarities.sort(key=lambda x: -x[1])
        
        results = []
        for idx, sim in similarities[:k]:
            q = self.questions[idx]
            try:
                assistant = q.get("assistant", "{}")
                data = json.loads(assistant)
                soru = data.get("soru", "")
                if soru and "numaralanmış" not in soru.lower():
                    results.append({
                        "soru": soru,
                        "similarity": float(sim)
                    })
            except:
                pass
        
        return results
    
    def get_reference_text(self, konu: str, alt_konu: str, zorluk: str = "orta") -> str:
        """Referans soruları metin olarak döndürür."""
        refs = self.find_similar(konu, alt_konu, zorluk, k=2)
        
        if not refs:
            return ""
        
        lines = ["[Referans Sorular:]"]
        for i, r in enumerate(refs, 1):
            soru = r["soru"][:100]
            lines.append(f"{i}. {soru}...")
        
        return "\n".join(lines)


# Singleton instance
_rag_instance = None

def get_rag() -> SimpleRAGv2:
    """RAG singleton döndürür."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = SimpleRAGv2()
    return _rag_instance


def initialize_rag(data_path: str, force: bool = False):
    """RAG'ı başlatır."""
    rag = get_rag()
    cache_dir = os.path.dirname(data_path)
    rag.initialize(cache_dir=cache_dir)
    rag.build_index(data_path, force=force)
    return rag


if __name__ == "__main__":
    # Test
    data_path = "data/lgs_finetune_data_v8_full_rag.jsonl"
    rag = initialize_rag(data_path, force=True)
    
    print("\n" + "="*60)
    print("TEST: Benzer sorular bulma")
    print("="*60)
    
    refs = rag.get_reference_text("Paragraf", "Ana Düşünce", "orta")
    print(refs)
    
    print("\n" + "="*60)
    refs = rag.get_reference_text("Cümlede Anlam", "Sebep-Sonuç", "zor")
    print(refs)
