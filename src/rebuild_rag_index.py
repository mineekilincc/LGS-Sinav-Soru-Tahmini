import os
import sys
import json

# Proje kök dizinini path'e ekle
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.rag_manager import SimpleRAG

def rebuild_index():
    print("🔄 RAG Index Yeniden Oluşturuluyor...")
    
    # 1. Veri setini yükle
    data_path = os.path.join(project_root, "data", "merged_dataset.json")
    print(f"📖 Veri seti okunuyor: {data_path}")
    
    with open(data_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    print(f"📊 Toplam Soru: {len(questions)}")
    
    # 2. RAG Manager'ı başlat
    rag = SimpleRAG()
    rag.initialize()
    
    # 3. Index oluştur (Force rebuild)
    # Cache path: root/data/rag_index.pkl
    rag.build_index(questions, force=True)
    
    print(f"✅ RAG Index başarıyla oluşturuldu.")
    
    # Test Sorgusu
    test_query = "Yazım Kuralları"
    print(f"\n🧪 Test Sorgusu: '{test_query}'")
    results = rag.find_similar(test_query, k=3)
    
    for i, res in enumerate(results, 1):
        print(f"{i}. Benzerlik: {res['similarity']:.4f} - Soru: {res['soru_kökü'][:100]}...")

if __name__ == "__main__":
    rebuild_index()
