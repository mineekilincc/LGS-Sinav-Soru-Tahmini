# -*- coding: utf-8 -*-
"""
LGS RAG Manager - Basit Versiyon (NumPy tabanlı)
=================================================
Bağımlılık sorunu olmadan çalışan basit RAG sistemi.
Cosine similarity ile benzer soru bulma.
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
    print("⚠ SentenceTransformers yüklü değil. 'pip install sentence-transformers' ile yükleyin.")


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """İki vektör arasındaki cosine similarity hesaplar."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


class SimpleRAG:
    """Basit NumPy tabanlı RAG sistemi."""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Args:
            model_name: Embedding modeli 
            (multilingual model kullanıyoruz çünkü BERTurk yüklemesi uzun sürebilir)
        """
        self.model_name = model_name
        self.model = None
        self.embeddings = None
        self.questions = None
        self.index_path = None
        
    def initialize(self, cache_dir: str = "./data"):
        """Model ve cache'i başlatır."""
        if not SBERT_AVAILABLE:
            raise ImportError("SentenceTransformers gerekli: pip install sentence-transformers")
        
        print(f"🔄 Embedding model yükleniyor: {self.model_name}...")
        self.model = SentenceTransformer(self.model_name)
        self.index_path = os.path.join(cache_dir, "rag_index.pkl")
        print("✓ Model hazır.")
        
    def _create_embedding_text(self, question: Dict[str, Any]) -> str:
        """Soru kaydından embedding için metin oluşturur."""
        parts = []
        
        # Konu bilgisi
        if question.get("konu_basligi"):
            parts.append(f"Konu: {question['konu_basligi']}")
        if question.get("alt_konu_basligi"):
            parts.append(f"Alt Konu: {question['alt_konu_basligi']}")
        
        # Metin (varsa)
        metin = question.get("metin", "")
        if metin and metin != "yok" and "Metin bulunmamaktadır" not in metin:
            parts.append(f"Metin: {metin[:300]}")  # Max 300 karakter
        
        # Soru kökü
        if question.get("soru_kökü"):
            parts.append(f"Soru: {question['soru_kökü'][:200]}")
        
        return " ".join(parts)
    
    def build_index(self, questions: List[Dict[str, Any]], force: bool = False):
        """Soru listesinden embedding index oluşturur."""
        if not self.model:
            raise RuntimeError("Önce initialize() çağırın.")
        
        # Cache kontrolü
        if not force and os.path.exists(self.index_path):
            print("📂 Mevcut index yükleniyor...")
            self.load_index()
            if len(self.questions) == len(questions):
                print(f"✓ Index hazır: {len(self.questions)} soru")
                return
            print("⚠ Soru sayısı değişmiş, yeniden indexleniyor...")
        
        print(f"🔄 {len(questions)} soru indexleniyor...")
        
        self.questions = questions
        texts = [self._create_embedding_text(q) for q in questions]
        
        # Batch halinde embedding oluştur
        self.embeddings = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        
        # Kaydet
        self.save_index()
        print(f"✓ Index hazır: {len(self.questions)} soru")
    
    def save_index(self):
        """Index'i diske kaydeder."""
        if self.embeddings is None or self.questions is None:
            return
        
        data = {
            "embeddings": self.embeddings,
            "questions": self.questions,
            "model_name": self.model_name
        }
        
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        with open(self.index_path, 'wb') as f:
            pickle.dump(data, f)
        print(f"💾 Index kaydedildi: {self.index_path}")
    
    def load_index(self):
        """Index'i diskten yükler."""
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(f"Index bulunamadı: {self.index_path}")
        
        with open(self.index_path, 'rb') as f:
            data = pickle.load(f)
        
        self.embeddings = data["embeddings"]
        self.questions = data["questions"]
        print(f"📂 Index yüklendi: {len(self.questions)} soru")
    
    def find_similar(
        self, 
        query: str, 
        k: int = 3, 
        filter_topic: Optional[str] = None,
        topic_weight: float = 3.0,
        balance_difficulty: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Sorguya en benzer k soruyu bulur (Metadata-Aware).
        
        Args:
            query: Arama sorgusu
            k: Döndürülecek sonuç sayısı
            filter_topic: Sadece bu konudaki soruları ara
            topic_weight: Konu eşleşmesine verilecek ek ağırlık (varsayılan: 3.0)
            balance_difficulty: Farklı zorluk seviyelerinden dengeli seçim yap
        """
        if self.embeddings is None or not self.model:
            raise RuntimeError("Önce initialize() ve build_index() çağırın.")
        
        # Query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
        
        # Tüm sorularla similarity hesapla
        similarities = []
        for i, emb in enumerate(self.embeddings):
            # Temel cosine similarity
            base_sim = cosine_similarity(query_embedding, emb)
            
            # Konu filtresi
            if filter_topic and self.questions[i].get("konu_basligi") != filter_topic:
                similarities.append(-1)  # Filtrelenen sorular için düşük skor
                continue
            
            # Metadata-Aware Scoring: Konu eşleşmesi varsa bonus ver
            final_sim = base_sim
            if filter_topic:
                question_topic = self.questions[i].get("konu_basligi", "")
                if question_topic == filter_topic:
                    # Konu eşleşmesi için ağırlık ekle
                    final_sim = base_sim * topic_weight
            
            similarities.append(final_sim)
        
        # Top-k bul
        top_indices = np.argsort(similarities)[-k*3:][::-1]  # 3x al, sonra dengele
        
        # Zorluk dengeleme
        if balance_difficulty and len(top_indices) >= k:
            difficulty_groups = {'kolay': [], 'orta': [], 'zor': []}
            for idx in top_indices:
                if similarities[idx] > 0:
                    diff = self.questions[idx].get('zorluk', 'orta')
                    difficulty_groups.get(diff, difficulty_groups['orta']).append(idx)
            
            # Her gruptan dengeli seç
            balanced_indices = []
            for _ in range(k):
                for diff in ['kolay', 'orta', 'zor']:
                    if difficulty_groups[diff]:
                        balanced_indices.append(difficulty_groups[diff].pop(0))
                        if len(balanced_indices) >= k:
                            break
                if len(balanced_indices) >= k:
                    break
            
            top_indices = balanced_indices[:k]
        else:
            top_indices = top_indices[:k]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:  # Filtrelenmemiş olanlar
                q = self.questions[idx]
                results.append({
                    "soru_id": q.get("soru_id", ""),
                    "similarity": float(similarities[idx]),
                    "konu_basligi": q.get("konu_basligi", ""),
                    "alt_konu_basligi": q.get("alt_konu_basligi", ""),
                    "zorluk": q.get("zorluk", "orta"),
                    "soru_kökü": q.get("soru_kökü", ""),
                    "metin": q.get("metin", "")[:200] + "..." if len(q.get("metin", "")) > 200 else q.get("metin", ""),
                    "question": q  # Tam soru objesi
                })
        
        return results
    
    def find_similar_strict(
        self,
        query: str,
        k: int = 4,
        topic: str = None,
        subtopic: str = None,
        must_have_keywords: List[str] = None,
        must_not_have: List[str] = None
    ) -> List[Dict]:
        """
        Sıkı metadata ve keyword filtresi ile benzer sorular bulur.
        
        Args:
            query: Arama sorgusu
            k: Döndürülecek sonuç sayısı
            topic: Konu filtresi (zorunlu eşleşme)
            subtopic: Alt konu filtresi (zorunlu eşleşme)
            must_have_keywords: Soru kökünde OLMASI gereken kelimeler (en az biri)
            must_not_have: Soru kökünde ve metinde OLMAMASI gereken kelimeler
            
        Returns:
            Filtrelenmiş soru listesi (similarity azalan sırada)
        """
        if self.embeddings is None or not self.model:
            raise RuntimeError("Önce initialize() ve build_index() çağırın.")
        
        # Query embedding
        query_embedding = self.model.encode([query], convert_to_numpy=True)[0]
        
        # Filtre uygula
        filtered_questions = []
        filtered_embeddings = []
        
        for i, q in enumerate(self.questions):
            # 1. Konu filtresi (zorunlu)
            if topic and q.get("konu_basligi") != topic:
                continue
            
            # 2. Alt konu filtresi (zorunlu)
            if subtopic and q.get("alt_konu_basligi") != subtopic:
                continue
            
            # 3. Must have keywords (soru kökünde en az biri olmalı)
            if must_have_keywords:
                soru_koku = q.get("soru_kökü", "").lower()
                if not any(kw.lower() in soru_koku for kw in must_have_keywords):
                    continue
            
            # 4. Must not have keywords (soru kökü VE metinde olmamalı)
            if must_not_have:
                soru_koku = q.get("soru_kökü", "").lower()
                metin = q.get("metin", "").lower()
                combined_text = soru_koku + " " + metin
                
                if any(kw.lower() in combined_text for kw in must_not_have):
                    continue
            
            # Filtreyi geçti
            filtered_questions.append(q)
            filtered_embeddings.append(self.embeddings[i])
        
        # Filtrelenmiş sorular yoksa boş dön
        if not filtered_questions:
            print(f"⚠️ Filtreler sonrası hiç soru bulunamadı (topic={topic}, subtopic={subtopic})")
            return []
        
        # Similarity hesapla
        similarities = []
        for emb in filtered_embeddings:
            sim = cosine_similarity(query_embedding, emb)
            similarities.append(sim)
        
        # Top-k bul
        top_indices = np.argsort(similarities)[-k:][::-1]
        
        results = []
        for idx in top_indices:
            q = filtered_questions[idx]
            results.append({
                "soru_id": q.get("soru_id", ""),
                "similarity": float(similarities[idx]),
                "konu_basligi": q.get("konu_basligi", ""),
                "alt_konu_basligi": q.get("alt_konu_basligi", ""),
                "zorluk": q.get("zorluk", "orta"),
                "soru_kökü": q.get("soru_kökü", ""),
                "metin": q.get("metin", "")[:200] + "..." if len(q.get("metin", "")) > 200 else q.get("metin", ""),
                "question": q
            })
        
        return results

    
    def get_full_examples(self, konu: str, alt_konu: str, k: int = 3, min_similarity: float = 0.3) -> List[str]:
        """
        Few-shot öğrenme için tam soru örnekleri döndürür.
        
        Args:
            konu: Ana konu
            alt_konu: Alt konu
            k: Örnek sayısı
            min_similarity: Minimum benzerlik eşiği
        
        Returns:
            List[str]: Formatlanmış tam soru örnekleri
        """
        query = f"{konu} {alt_konu}"
        results = self.find_similar(query, k=k*2, filter_topic=konu)  # 2x al, filtreleme için
        
        examples = []
        for r in results:
            if r["similarity"] < min_similarity:
                continue
            
            q = r.get("question", {})
            
            # Metin kontrolü
            metin = q.get("metin", "")
            if not metin or metin == "yok" or "Metin bulunmamaktadır" in metin:
                continue
            
            # Şıklar kontrolü
            sik_a = q.get("şık_a", "")
            sik_b = q.get("şık_b", "")
            sik_c = q.get("şık_c", "")
            sik_d = q.get("şık_d", "")
            
            if not all([sik_a, sik_b, sik_c, sik_d]):
                continue
            
            # Format oluştur
            example = f"""Metin: {metin}

Soru: {q.get("soru_kökü", "")}

A) {sik_a}
B) {sik_b}
C) {sik_c}
D) {sik_d}

Doğru Cevap: {q.get("doğru_cevap", "").upper()}"""
            
            examples.append(example)
            
            if len(examples) >= k:
                break
        
        return examples


def main():
    """RAG sistemini test eder."""
    # Veri yükle
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    data_path = os.path.join(project_dir, "data", "merged_dataset_reclassified_fixed.json")
    
    if not os.path.exists(data_path):
        print(f"❌ Veri dosyası bulunamadı: {data_path}")
        print("Önce merge_data.py çalıştırın.")
        return
    
    with open(data_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    
    print(f"📊 Yüklenen soru sayısı: {len(questions)}")
    
    # RAG oluştur
    cache_dir = os.path.join(project_dir, "data")
    rag = SimpleRAG()
    rag.initialize(cache_dir=cache_dir)
    
    # Index oluştur
    rag.build_index(questions)
    
    # Test sorguları
    print("\n" + "=" * 60)
    print("TEST 1: 'Paragraf ana düşünce orta zorluk'")
    print("=" * 60)
    
    results = rag.find_similar("Paragraf ana düşünce orta zorluk", k=3)
    
    for i, r in enumerate(results, 1):
        print(f"\n{i}. Benzer Soru (similarity: {r['similarity']:.4f})")
        print(f"   ID: {r['soru_id']}")
        print(f"   Konu: {r['konu_basligi']} / {r['alt_konu_basligi']}")
        print(f"   Soru: {r['soru_kökü'][:80]}...")
    
    # Test 2: Konu filtreli arama
    print("\n" + "=" * 60)
    print("TEST 2: 'Deyim anlamı' (filtre: Cümlede Anlam)")
    print("=" * 60)
    
    results = rag.find_similar("Deyim anlamı", k=3, filter_topic="Cümlede Anlam")
    
    for i, r in enumerate(results, 1):
        print(f"\n{i}. Benzer Soru (similarity: {r['similarity']:.4f})")
        print(f"   ID: {r['soru_id']}")
        print(f"   Konu: {r['konu_basligi']} / {r['alt_konu_basligi']}")
    
    print("\n✅ RAG sistemi hazır!")


if __name__ == "__main__":
    main()
