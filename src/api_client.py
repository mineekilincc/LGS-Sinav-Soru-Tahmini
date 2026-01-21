# -*- coding: utf-8 -*-
"""
LGS API Client - Farkındalık Paragraf Üretimi
==============================================
Gemini, Groq API'leri için fallback destekli client.
"""

import os
import json
import time
from typing import Optional, List, Dict, Union, Dict, Any

# API değişkenleri (env'den veya config'den)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
COLAB_API_URL = os.environ.get("COLAB_API_URL", "")

# Fallback sırası (Colab varsa önce o entegre modeldir)

class APIClient:
    """API client - fallback mekanizmalı."""
    
    def __init__(self, gemini_key: str, groq_key: str):
        self.gemini_key = gemini_key
        self.groq_key = groq_key
        # Öncelik sırası: GROQ first (Colab V4 bozuk - garbage output)
        self.priority = ["groq", "gemini", "colab"]
        
        # Colab API URL (.env'den veya sabit)
        self.colab_url = os.getenv("COLAB_API_URL")
        
        # SSL doğrulamasını geliştirme ortamı için kapat (Cloudflare/Ngrok için gerekli olabiliyor)
        self.verify_ssl = False 
        self.last_api_used = None
        
    
    def _call_colab(self, prompt: Union[str, Dict]) -> Optional[str]:
        """Colab (Fine-tuned Model) API çağrısı + Farkındalık Konuları."""
        if not self.colab_url:
            return None
            
        try:
            import requests
            import urllib3
            import random
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Farkındalık konuları havuzu
            AWARENESS_TOPICS = [
                "Yapay zekâ ve günlük yaşam",
                "Dijital okuryazarlık ve internet güvenliği",
                "Küresel ısınma ve iklim değişikliği",
                "Su tasarrufu ve temiz su kaynakları",
                "Deprem bilinci ve afet hazırlığı",
                "Okuma alışkanlığı ve kitabın önemi",
                "Çevre kirliliği ve geri dönüşüm",
                "Sağlıklı beslenme ve spor",
                "Sosyal medya ve dijital bağımlılık",
                "Biyolojik çeşitlilik ve ekosistem",
                "Yenilenebilir enerji kaynakları",
                "Bilim ve teknolojinin topluma etkisi"
            ]
            
            # Prompt enhancement
            if isinstance(prompt, dict):
                user_content = prompt.get("user", "")
                
                # Rastgele farkındalık konusu ekle (30% şans)
                enhanced_user = user_content
                if random.random() < 0.3:
                    topic = random.choice(AWARENESS_TOPICS)
                    enhanced_user = f"{user_content}\n\n💡 FARK INDALIK KONUSU: {topic}\nMetinde bu konuyu işle!"
                
                # Metin uzunluğu vurgusu
                enhanced_user += "\n\n⚠️ ÖNEMLİ: Metin TAM 80-150 kelime olmalı! Kısa metinler kabul edilmez!"
                
                payload = {"prompt": enhanced_user}
            else:
                payload = {"prompt": prompt}

            url = f"{self.colab_url.rstrip('/')}/generate"
            response = requests.post(url, json=payload, timeout=120, verify=False)
            
            if response.status_code == 200:
                self.last_api_used = "colab"
                return response.json().get("result", "")
            else:
                print(f"⚠️ Colab hatası: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"⚠️ Colab bağlantı hatası: {e}")
            return None

    def _call_gemini(self, prompt: Union[str, Dict]) -> Optional[str]:
        """Gemini API çağrısı."""
        if not self.gemini_key:
            return None
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Gemini system prompt desteği (basic)
            if isinstance(prompt, dict):
                # Gemini Pro system promptu constructor'da alıyor ama burada basitçe birleştiriyoruz
                final_str = f"SYSTEM: {prompt.get('system', '')}\n\nUSER: {prompt.get('user', '')}"
            else:
                final_str = prompt
                
            response = model.generate_content(final_str)
            self.last_api_used = "gemini"
            return response.text
        except Exception as e:
            print(f"⚠️ Gemini hatası: {e}")
            return None
    
    def _call_groq(self, prompt: Union[str, Dict]) -> Optional[str]:
        """Groq API + Ultra-Strict Rules + Topic-Specific Instructions."""
        if not self.groq_key:
            return None
        
        try:
            from groq import Groq
            import random
            import re
            client = Groq(api_key=self.groq_key)
            
            # Ultra-Strict System Prompt
            ULTRA_STRICT_SYSTEM = """Sen MEB LGS Türkçe soru yazarısın.

⛔ KESİN YASAKLAR (BİRİNİ İHLAL EDERSEN SORU REDDEDİLİR):
1. ❌ "Numaralanmış cümle", "I., II., III.", "1., 2., 3." YASAK!
2. ❌ Yabancı dil (İngilizce, Çince, Vietnamca vb.) YASAK!
3. ❌ Bitişik yazım hataları YASAK! "bilim insanları" (✓)
4. ❌ Alt konu dışına çıkma YASAK!

✅ ZORUNLU:
- %100 Türkçe (TDK kuralları)
- Alt konuya TAM uyum
- Metin 120-180 kelime (PARAGRAF için)
- JSON formatı

📝 METİN YAZMA KURALLARI:
- Giriş cümlesi: Konuyu tanıt (20-30 kelime)
- Gelişme: 3-4 destekleyici cümle, örnekler ver (80-120 kelime)
- Sonuç: Özet veya çıkarım (20-30 kelime)
- Toplam: 5-7 cümle, akıcı ve bağlantılı

JSON:
{"metin": "...", "soru": "...", "sik_a": "...", "sik_b": "...", "sik_c": "...", "sik_d": "...", "dogru_cevap": "A"}"""
            
            # Topic-Specific Rules
            TOPIC_RULES = {
                "Deyim": {
                    "text_required": True,
                    "instructions": """
🎯 ALT KONU: DEYİM
- Metinde bir deyim kullan (örn: "elinden geleni yapmak", "göz kulak olmak")
- Soru: "Bu parçada kullanılan deyimin anlamı..." veya "...deyim vardır?"
- ❌ YASAK: "Numaralanmış cümle" formatı kullanma!
- ✅ DOĞRU: Deyimi doğal metne yerleştir
"""
                },
                "Koşul": {
                    "text_required": True,
                    "instructions": """
🎯 ALT KONU: KOŞUL ANLAMI
- Metinde koşul ifadesi kullan: "eğer", "-sa/-se", "şayet", "-dığında"
- Soru: "Bu cümlede koşul anlamı hangi sözcükle sağlanmıştır?"
- ❌ YASAK: "Numaralanmış cümle" formatı kullanma!
- ✅ DOĞRU: Koşul cümlesini doğal akışta kullan
"""
                },
                "Anlatım Biçimi": {
                    "text_required": True,
                    "instructions": """
🎯 ALT KONU: ANLATIM BİÇİMİ
⚠️ ÇOK ÖNEMLİ: Sadece anlatım türünü sor!

✅ DOĞRU SORU KÖKLERI:
- "Bu metnin anlatım biçimi aşağıdakilerden hangisidir?"
- "Bu metinde hangi anlatım türü kullanılmıştır?"
- "Bu parçada ağırlıklı olarak hangi anlatım biçimi kullanılmıştır?"

✅ DOĞRU ŞIKLAR (Sadece bunlar!):
- Öyküleme (olay anlatımı)
- Betimleme (tasvir, duyusal ayrıntılar)
- Açıklama (bilgi aktarımı, tanım)
- Tartışma (görüş savunma, kanıt)

❌ YASAK SORU TİPLERİ:
- "Bu parçadan ... yargıların hangisine ulaşılamaz?" (Ana düşünce sorusu!)
- "Bu parçanın ana düşüncesi..." (Ana düşünce sorusu!)
- "Bu parçaya en uygun başlık..." (Başlık sorusu!)

ÖRNEK FORMAT:
{
  "metin": "Ormanın derinliklerinde, yüksek çamların arasında küçük bir kulübe vardı. Kulübenin önündeki çimenler yeşildi, çiçekler rengârenkti. Kuşlar şakıyordu, arılar vızıldıyordu...",
  "soru": "Bu metnin anlatım biçimi aşağıdakilerden hangisidir?",
  "sik_a": "Öyküleme",
  "sik_b": "Betimleme",
  "sik_c": "Açıklama",
  "sik_d": "Tartışma",
  "dogru_cevap": "B"
}
"""
                },
                "Ana Düşünce": {
                    "text_required": True,
                    "instructions": """
🎯 ALT KONU: ANA DÜŞÜNCE
- Soru: "Bu parçanın ana düşüncesi..." veya "Bu metinde asıl anlatılmak istenen..."
- ❌ YASAK: Başlık sorusu sorma!
- ✅ DOĞRU: Ana düşünceyi sor
"""
                },
                "Sebep-Sonuç": {
                    "text_required": True,
                    "instructions": """
🎯 ALT KONU: SEBEP-SONUÇ
- Metinde sebep-sonuç ilişkisi kur ("çünkü", "bu nedenle", "bu yüzden")
- Soru: "Bu parçada sebep-sonuç ilişkisi..." veya "...nedeni/sonucu..."
- ❌ YASAK: "Numaralanmış cümle" formatı kullanma!
"""
                },
                "Öznel-Nesnel": {
                    "text_required": True,
                    "instructions": """
🎯 ALT KONU: ÖZNEL-NESNEL YARGI
- Metinde hem öznel hem nesnel cümleler kullan
- Öznel: "güzel", "bence", "sanırım" / Nesnel: rakamlar, olgular
- Soru: "Aşağıdaki cümlelerin hangisi öznel/nesnel yargı içerir?"
- ❌ YASAK: "Numaralanmış cümle" formatı kullanma!
"""
                },
                "Noktalama": {
                    "text_required": False,  # ⚠️ METİN GEREKSIZ!
                    "instructions": """
🎯 ALT KONU: NOKTALAMA
⚠️ ÖNEMLİ: Bu soru tipi için PARAGRAF METNİ GEREKSIZ!

- Soru: "Aşağıdaki cümlelerin hangisinde virgül/nokta/iki nokta doğru kullanılmıştır?"
- Şıklar: Her şık bir cümle olmalı, noktalama farklılıkları göster
- ❌ YASAK: Uzun paragraf metni yazma!
- ✅ DOĞRU: Sadece soru + 4 örnek cümle şık

ÖRNEK FORMAT:
{
  "metin": "",  ← BOŞ BIRAK!
  "soru": "Aşağıdaki cümlelerin hangisinde virgül doğru kullanılmıştır?",
  "sik_a": "Kitap, defter kalem aldım.",
  "sik_b": "Kitap, defter, kalem aldım.",
  "sik_c": "Kitap defter, kalem aldım.",
  "sik_d": "Kitap defter kalem, aldım.",
  "dogru_cevap": "B"
}
"""
                },
                "Yazım Yanlışı": {
                    "text_required": False,  # ⚠️ METİN GEREKSIZ!
                    "instructions": """
🎯 ALT KONU: YAZIM YANLIŞI
⚠️ ÖNEMLİ: Bu soru tipi için PARAGRAF METNİ GEREKSIZ!

- Soru: "Aşağıdaki cümlelerin hangisinde yazım yanlışı vardır?"
- Şıklar: Her şık bir cümle, biri yanlış yazım içermeli
- ❌ YASAK: Uzun paragraf metni yazma!
- ✅ DOĞRU: Sadece soru + 4 örnek cümle şık

ÖRNEK FORMAT:
{
  "metin": "",  ← BOŞ BIRAK!
  "soru": "Aşağıdaki cümlelerin hangisinde yazım yanlışı vardır?",
  "sik_a": "Bilim insanları yeni keşifler yapar.",
  "sik_b": "Biliminsanları yeni keşifler yapar.",
  "sik_c": "Bilim adamları araştırma yapar.",
  "sik_d": "Araştırmacılar deney yapar.",
  "dogru_cevap": "B"
}
"""
                },
                "Fiilimsiler": {
                    "text_required": False,  # ⚠️ METİN GEREKSIZ!
                    "instructions": """
🎯 ALT KONU: FİİLİMSİLER
⚠️ ÖNEMLİ: Bu soru tipi için PARAGRAF METNİ GEREKSIZ!

- Soru: "Aşağıdaki cümlelerin hangisinde fiilimsi vardır?" veya "...isim-fiil/sıfat-fiil/zarf-fiil..."
- Şıklar: Her şık bir cümle, fiilimsi örnekleri
- ❌ YASAK: Uzun paragraf metni yazma!
- ✅ DOĞRU: Sadece soru + 4 örnek cümle şık

ÖRNEK FORMAT:
{
  "metin": "",  ← BOŞ BIRAK!
  "soru": "Aşağıdaki cümlelerin hangisinde isim-fiil vardır?",
  "sik_a": "Koşmak sağlıklıdır.",
  "sik_b": "Koşan çocuk yoruldu.",
  "sik_c": "Koşarak geldi.",
  "sik_d": "Koştu ve yoruldu.",
  "dogru_cevap": "A"
}
"""
                }
            }
            
            # RAG Knowledge
            RAG_KNOWLEDGE = {
                "Paragraf": "Ana düşünce metnin tümünü kapsayan en genel yargıdır. Başlık kısa ve öz olmalı. Çeldiriler metindeki kelimelerle benzer ama yanlış anlamda olmalı.",
                "Cümlede Anlam": "Sebep-sonuç ilişkisi net olmalı. Öznel yargı kişisel görüş, nesnel yargı kanıtlanabilir bilgidir.",
                "Sözcükte Anlam": "Çok anlamlılık: Aynı sözcük farklı anlamlarda. Eş anlamlılık: Başka sözcük aynı anlam.",
                "Dil Bilgisi": "Fiilimsiler: isim-fiil, sıfat-fiil, zarf-fiil. Her birinin özellikleri belirgindir.",
                "Yazım Kuralları": "Noktalama ve yazım kurallarını test et. Bitişik-ayrı yazım önemli."
            }
            
            # Awareness Topics
            AWARENESS_TOPICS = [
                "Yapay zekâ ve günlük yaşam",
                "Dijital okuryazarlık ve internet güvenliği",
                "Küresel ısınma ve iklim değişikliği",
                "Su tasarrufu ve temiz su kaynakları",
                "Deprem bilinci ve afet hazırlığı",
                "Okuma alışkanlığı ve kitabın önemi",
                "Çevre kirliliği ve geri dönüşüm",
                "Sağlıklı beslenme ve spor",
                "Sosyal medya ve dijital bağımlılık",
                "Biyolojik çeşitlilik ve ekosistem",
                "Yenilenebilir enerji kaynakları",
                "Bilim ve teknolojinin topluma etkisi"
            ]
            
            # Build enhanced prompt
            messages = []
            if isinstance(prompt, dict):
                user_content = prompt.get("user", "")
                
                # Extract konu/alt_konu
                konu_match = re.search(r'\*\*Konu:\*\*\s*([^\n*]+)', user_content)
                alt_konu_match = re.search(r'\*\*Alt Konu:\*\*\s*([^\n*]+)', user_content)
                
                konu = konu_match.group(1).strip() if konu_match else ""
                alt_konu = alt_konu_match.group(1).strip() if alt_konu_match else ""
                
                enhanced_user = user_content
                
                # Add RAG knowledge
                rag_hint = RAG_KNOWLEDGE.get(konu, "")
                if rag_hint:
                    enhanced_user += f"\n\n💡 STRATEJİK BİLGİ:\n{rag_hint}"
                
                # Add topic-specific rules
                topic_config = TOPIC_RULES.get(alt_konu, {})
                topic_instructions = topic_config.get("instructions", "")
                text_required = topic_config.get("text_required", True)
                
                if topic_instructions:
                    enhanced_user += f"\n\n{topic_instructions}"
                
                # Conditional text length requirement
                if text_required:
                    # Add awareness topic (40% chance)
                    if random.random() < 0.4:
                        topic = random.choice(AWARENESS_TOPICS)
                        enhanced_user += f"\n\n🌍 FARK INDALIK KONUSU: {topic}\nMetinde bu konuyu işle ve 120-180 kelime TAM tut!"
                else:
                    # No text needed - emphasize
                    enhanced_user += "\n\n⚠️ ÖNEMLİ: Bu soru tipi için PARAGRAF METNİ GEREKSIZ! Metin alanını BOŞ BIRAK!"
                
                # Add ultra-strict warnings
                enhanced_user += """

⚠️ SON UYARILAR:
1. "Numaralanmış cümle", "I., II., III.", "1., 2., 3." KULLANMA!
2. Yabancı kelime KULLANMA! (İngilizce, Çince vb.)
3. Metin MUTLAKA 120-180 kelime olmalı! (Paragraf soruları için)
4. Alt konuya %100 uygun soru sor!
5. Sadece JSON döndür, başka hiçbir şey yazma!

⚠️ ANLATIM BİÇİMİ İÇİN ÖZEL UYARI:
- "Bu parçadan ... yargıların hangisine ulaşılamaz?" YASAK!
- "Bu parçanın ana düşüncesi..." YASAK!
- SADECE: "Bu metnin anlatım biçimi aşağıdakilerden hangisidir?"
- ŞIKLAR SADECE: Öyküleme, Betimleme, Açıklama, Tartışma

📝 METİN YAPISI (Paragraf için):
- 1. cümle: Giriş/Konu tanıtımı (20-30 kelime)
- 2-5. cümleler: Gelişme/Örnekler/Açıklamalar (80-120 kelime)
- 6-7. cümleler: Sonuç/Özet/Çıkarım (20-30 kelime)
- Toplam: 5-7 cümle, akıcı ve mantıklı bağlantılarla

Örnek yapı:
"[Konu tanıtımı]. [Detay 1]. [Detay 2]. [Örnek]. [Açıklama]. [Sonuç/Özet]."
"""
                
                messages.append({"role": "system", "content": ULTRA_STRICT_SYSTEM})
                messages.append({"role": "user", "content": enhanced_user})
            else:
                messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=2048,
                temperature=0.5,
            )
            self.last_api_used = "groq"
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ Groq hatası: {e}")
            return None
    
    def generate(self, prompt: str) -> Optional[str]:
        """
        Fallback mekanizmalı API çağrısı.
        Sırasıyla: Colab -> Groq -> Gemini
        """
        print(f"🔧 DEBUG: Colab URL = {self.colab_url}")
        print(f"🔧 DEBUG: API Öncelik Sırası = {self.priority}")
        
        for api in self.priority:
            print(f"⏳ {api.upper()} deneniyor...")
            
            if api == "colab":
                result = self._call_colab(prompt)
            elif api == "groq":
                result = self._call_groq(prompt)
            elif api == "gemini":
                result = self._call_gemini(prompt)
            else:
                continue
            
            if result:
                print(f"✅ {api.upper()} başarılı!")
                return result
            else:
                print(f"❌ {api.upper()} başarısız, sıradakine geçiliyor...")
            
            time.sleep(0.5)  # Rate limit için bekle
        
        return None
    
    def generate_awareness_paragraph(self, topic: str, word_count: int = 45) -> Optional[str]:
        """
        Farkındalık konusunda paragraf üretir.
        
        Args:
            topic: Farkındalık konusu (örn: "Yapay zekâ ve gelecek")
            word_count: Hedef kelime sayısı
        
        Returns:
            Üretilen paragraf veya None
        """
        prompt = f"""LGS Türkçe sınavı için 8. sınıf öğrencilerine uygun bir paragraf yaz.

KONU: {topic}

KURALLAR:
- Yaklaşık {word_count} kelime olmalı
- Nesnel ve bilgilendirici bir dil kullan
- Karmaşık terimlerden kaçın
- 2-4 cümle olmalı
- Paragrafın bir ana düşüncesi olmalı

Sadece paragrafı yaz, başka hiçbir şey ekleme."""
        
        return self.generate(prompt)


def get_awareness_paragraph(topic: str, api_client: APIClient = None) -> str:
    """
    Farkındalık paragrafı döndürür.
    Önce API dener, başarısız olursa fallback kullanır.
    """
    if api_client:
        result = api_client.generate_awareness_paragraph(topic)
        if result:
            return result.strip()
    
    # Fallback
    for key, paragraph in FALLBACK_PARAGRAPHS.items():
        if key.lower() in topic.lower() or topic.lower() in key.lower():
            return paragraph.strip()
    
    # Genel fallback
    return list(FALLBACK_PARAGRAPHS.values())[0].strip()


class QuestionGeneratorAPI:
    """Soru üretim API'si - Gemini/Groq ile."""
    
    def __init__(self, gemini_key: str = None, groq_key: str = None):
        self.client = APIClient(gemini_key, groq_key)
    
    def generate_question(self, prompt: str) -> dict:
        """
        Prompt'tan soru üretir ve parse eder.
        
        Returns:
            dict: {metin, soru_koku, sik_a, sik_b, sik_c, sik_d, dogru_cevap}
        """
        response = self.client.generate(prompt)
        
        if not response:
            return {"error": "API yanıt vermedi", "raw": None}
        
        print(f"🔍 RAW RESPONSE: {response!r}")
        
        # Parse et
        return self._parse_question(response)
    
    def _parse_question(self, text: str) -> dict:
        """LLM çıktısını parse eder (JSON ve Text desteği)."""
        result = {
            "metin": "",
            "soru_koku": "",
            "sik_a": "",
            "sik_b": "",
            "sik_c": "",
            "sik_d": "",
            "dogru_cevap": "",
            "raw": text
        }
        
        # 1. Önce JSON parse etmeyi dene
        try:
            # Bazen başında/sonunda text olabilir, sadece { ... } arasını al
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                json_str = text[start:end+1]
                data = json.loads(json_str)
                
                # Alan eşleştirme (Model bazen farklı key kullanabiliyor)
                result["metin"] = data.get("metin", data.get("text", ""))
                
                # Soru kökü için çeşitli ihtimaller (Qwen2.5: soru_kalinlik)
                result["soru_koku"] = data.get("soru_koku", data.get("soru", data.get("soru_kalinlik", data.get("question", ""))))
                
                # Şıklar (sik_a, secenek_a, A, option_a vb.)
                result["sik_a"] = data.get("sik_a", data.get("secenek_a", data.get("A", data.get("sikA", ""))))
                result["sik_b"] = data.get("sik_b", data.get("secenek_b", data.get("B", data.get("sikB", ""))))
                result["sik_c"] = data.get("sik_c", data.get("secenek_c", data.get("C", data.get("sikC", ""))))
                result["sik_d"] = data.get("sik_d", data.get("secenek_d", data.get("D", data.get("sikD", ""))))
                
                # Doğru cevap
                correct = data.get("dogru_cevap", data.get("answer", data.get("correct_answer", data.get("dogruCevap", ""))))
                if correct and isinstance(correct, str):
                    result["dogru_cevap"] = correct.strip().upper()[-1] # "Cevap: B" gelirse B al
                
                # Eğer temel alanlar dolduysa dön
                if result["soru_koku"] and result["dogru_cevap"]:
                    return result
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"⚠️ JSON parsing error: {e}")

        # 2. JSON başarısızsa klasik Text Parsing (Fallback)
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
                # "Doğru Cevap: A" formatı. Önce :'den sonrasına bak.
                if ":" in line:
                    candidate = line.split(":")[-1].strip().upper()
                else:
                     # : yoksa sondan başa doğru bak veya kelimelere ayır
                    candidate = line.upper()
                
                # Candidate içindeki ilk geçerli A,B,C,D harfini bul (tercihen tek harfse)
                for char in candidate:
                    if char in "ABCD":
                        result["dogru_cevap"] = char
                        break
            elif current_section == "metin" and line:
                result["metin"] += " " + line
            elif current_section == "soru" and line:
                result["soru_koku"] += " " + line
        
        return result


# Farkındalık konuları için önceden hazırlanmış paragraflar (API yoksa kullanılır)
FALLBACK_PARAGRAPHS = {
    "Yapay zekâ ve gelecek": """Günümüzde yapay zekâ teknolojileri hayatımızın her alanında kullanılmaya başlandı. 
Akıllı asistanlardan sürücüsüz araçlara, tıbbi teşhislerden eğitime kadar pek çok alanda bu teknoloji önemli 
bir yer edindi. Uzmanlar, yapay zekânın gelecekte daha da yaygınlaşacağını ve toplumsal yapıyı köklü 
biçimde değiştireceğini öngörmektedir.""",
    
    "Deprem bilinci ve hazırlık": """Ülkemiz, aktif fay hatları üzerinde bulunduğu için deprem riski taşıyan 
bir coğrafyada yer almaktadır. Deprem öncesi, sırası ve sonrasında yapılması gerekenler konusunda 
toplumsal bilinç oluşturmak hayati önem taşımaktadır. Bu nedenle okullardan başlayarak tüm bireylerin 
deprem eğitimi alması gerekmektedir.""",
    
    "Küresel ısınma etkileri": """Küresel ısınma, atmosferdeki sera gazlarının artmasıyla birlikte Dünya'nın 
ortalama sıcaklığının yükselmesi olgusudur. Bu durum, buzulların erimesine, deniz seviyelerinin yükselmesine 
ve iklim düzensizliklerine neden olmaktadır. Bilim insanları, bu soruna karşı önlem alınmazsa gelecekte 
daha ciddi çevresel felaketler yaşanabileceği konusunda uyarıda bulunmaktadır.""",
    
    "Teknoloji bağımlılığı ve dijital detoks": """Akıllı telefonlar ve sosyal medya, günlük hayatımızın 
ayrılmaz bir parçası hâline geldi. Ancak bu teknolojilerin aşırı kullanımı, özellikle gençlerde bağımlılık 
benzeri davranışlara yol açabilmektedir. Uzmanlar, dijital cihazlardan belirli aralıklarla uzak durmanın 
ruh sağlığı açısından önemli olduğunu vurgulamaktadır.""",
}


def get_awareness_paragraph(topic: str, api_client: APIClient = None) -> str:
    """
    Farkındalık paragrafı döndürür.
    Önce API dener, başarısız olursa fallback kullanır.
    """
    if api_client:
        result = api_client.generate_awareness_paragraph(topic)
        if result:
            return result.strip()
    
    # Fallback
    for key, paragraph in FALLBACK_PARAGRAPHS.items():
        if key.lower() in topic.lower() or topic.lower() in key.lower():
            return paragraph.strip()
    
    # Genel fallback
    return list(FALLBACK_PARAGRAPHS.values())[0].strip()


def main():
    """Test."""
    print("=" * 60)
    print("API CLIENT TEST")
    print("=" * 60)
    
    client = APIClient()
    
    # Farkındalık paragrafı test
    topics = [
        "Yapay zekâ ve gelecek",
        "Deprem bilinci ve hazırlık",
        "Su tasarrufu ve küresel kriz"
    ]
    
    for topic in topics:
        print(f"\n📌 Konu: {topic}")
        paragraph = get_awareness_paragraph(topic, client)
        print(f"📝 Paragraf ({len(paragraph.split())} kelime):")
        print(paragraph[:200] + "..." if len(paragraph) > 200 else paragraph)
        print(f"🔧 Kullanılan API: {client.last_api_used or 'fallback'}")


if __name__ == "__main__":
    main()
