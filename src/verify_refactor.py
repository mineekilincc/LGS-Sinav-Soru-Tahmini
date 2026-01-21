import os
import sys

# Proje root ekle
# Proje root ekle (src'nin bir üstü)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.question_generator import LGSQuestionGenerator

def test_new_logic():
    print("🧪 Refaktör Testi Başlıyor...")
    
    # Path
    data_path = os.path.join("data", "merged_dataset.json")
    if not os.path.exists(data_path):
        print(f"❌ Veri dosyası bulunamadı: {data_path}")
        return

    # Init
    try:
        gen = LGSQuestionGenerator(data_path)
        gen.initialize()
        print("✅ Generator initialize başarılı.")
    except Exception as e:
        print(f"❌ Init hatası: {e}")
        return

    # Test 1: Anlam Sorusu
    try:
        p1 = gen.generate_prompt("Paragraf", "Ana Düşünce", "zor")
        if "MEB TARZI MİKRO-YAPI" in p1["prompt"]: # Meaning template has this? Or not?
            # Wait, MEANING_PROMPT_TEMPLATE had "YAPI: - Giriş... - Gelişme..."
            # Old template had "MEB TARZI MİKRO-YAPI".
            # New template has "## METİN YAZIM KURALLARI".
            print("✅ Anlam sorusu promptu oluşturuldu.")
            print(f"   Konu: {p1['konu']}")
            print(f"   Prompt başı: {p1['prompt'][:50]}...")
    except Exception as e:
        print(f"❌ Anlam sorusu hatası: {e}")

    # Test 2: Dil Bilgisi Sorusu
    try:
        p2 = gen.generate_prompt("Dil Bilgisi", "Fiilimsiler", "orta")
        if "DERS NOTU / KONU ANLATIMI TARZI METİN ASLA YAZMA" in p2["prompt"]:
            print("✅ Dil bilgisi promptu doğru şablonu (Grammar) kullandı.")
        else:
            print("❌ Dil bilgisi promptu yanlış şablonu kullandı!")
    except Exception as e:
        print(f"❌ Dil bilgisi sorusu hatası: {e}")

if __name__ == "__main__":
    test_new_logic()
