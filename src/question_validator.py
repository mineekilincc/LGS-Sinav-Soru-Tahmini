# -*- coding: utf-8 -*-
"""
LGS Soru Doğrulayıcı
===================
Üretilen soruların alt konuya uygunluğunu, yapısal doğruluğunu ve 
kalitesini doğrular. Hatalı soruların filtrelenmesini sağlar.
"""

import re
from typing import Dict, List, Optional


class QuestionValidator:
    """Soru doğrulama sınıfı."""
    
    # Alt konu bazlı anahtar kelimeler (GENİŞLETİLMİŞ - V4 model çıktılarına uyumlu)
    SUBTOPIC_KEYWORDS = {
        "Ana Düşünce": [
            # Pozitif kalıplar - çok geniş tutuyoruz
            "ana düşünce", "asıl düşünce", "parçanın konusu", 
            "anlatmak istediği", "anlatılmak istenen", "anlatmak istedikleri",
            "asıl anlatmak", "temel düşünce", "merkez düşünce",
            # Negatif kök kalıpları (ZOR sorular için)
            "ulaşılamaz", "çıkarılamaz", "söylenemez", "değinilmemiştir",
            "ulaşamaz", "çıkmaz", "söylenmez", "hangisine ulaşılabilir",
            # GENİŞ KALIPLAR - model çeşitli formatlarda soru üretebilir
            "buna göre", "hangisi", "parçadan", "metinden", "bu metnin",
            "aşağıdakilerden hangisi", "bu parçanın", "parçaya göre"
        ],
        "Yardımcı Düşünce": [
            "yardımcı düşünce", "destekleyen", "desteklemez"
        ],
        "Anlatım Biçimi": [
            "anlatım", "öyküleme", "betimleme", "açıklama", "tartışma", 
            "tür", "anlatım tarzı", "dil ve anlatım", "anlatım biçimi",
            # Negatif kök kalıpları
            "söylenemez", "kullanılmamıştır"
        ],
        "Başlık Bulma": [
            "başlık", "konusu", "en uygun başlık", "başlığı"
        ],
        "Sebep-Sonuç": [
            "sebep", "sonuç", "neden", "dolayı", "çünkü", "ilişki", 
            "nedeniyle", "sonucunda", "bunun nedeni", "bunun sonucu",
            "neden-sonuç", "neden-sonuç ilişkisi", "sebebi", "yol açar"
        ],
        "Koşul": ["koşul", "şart", "gerekli", "olması için", "-sa", "-se"],
        "Öznel-Nesnel": ["öznel", "nesnel", "kişisel görüş", "objektif", "yorum", "gerçek"],
        "Deyim": ["deyim", "atasözü", "altı çizili", "mecaz", "anlam"],
        "Noktalama": ["nokta", "virgül", "iki nokta", "noktalama", "tire", "kesme", "soru işareti"],
        "Yazım Yanlışı": ["yazım", "imla", "yanlış", "doğru yazılmış", "yazılan"],
        "Fiilimsiler": ["fiilimsi", "isim-fiil", "sıfat-fiil", "zarf-fiil", "-mak", "-me", "-ış", "-an", "-en", "-dık"],
        "Anlatım Bozukluğu": ["anlatım bozukluğu", "bozukluk", "düzeltilmeli"],
        "Çok Anlamlılık": ["çok anlamlı", "farklı anlam", "hangi anlamda", "kullanılmamıştır", "anlam"],
        "Yakın Anlam": ["yakın anlam", "anlamca yakın", "eş anlam"],
    }
    
    # Uyarı tetikleyen eşleşmeler (metinde olmaması gereken pattern'ler için)
    DANGEROUS_PATTERNS = {
        "numaralanmış cümle": [
            r'I\.', r'II\.', r'III\.', r'IV\.', r'V\.',  # I. II. III. formatı
            r'1\.', r'2\.', r'3\.', r'4\.', r'5\.',      # 1. 2. 3. formatı
            r'\(I\)', r'\(II\)', r'\(III\)', r'\(IV\)',  # (I) (II) (III) formatı
        ],
        "boş parantez": [r'\(\s*\)', r'\[\s*\]'],
    }
    
    def validate(
        self, 
        question: Dict[str, str], 
        alt_konu: str, 
        metin: str
    ) -> Dict[str, any]:
        """
        Soruyu doğrular.
        
        Args:
            question: Soru dict'i (soru_koku, sik_a/b/c/d, dogru_cevap)
            alt_konu: Alt konu başlığı
            metin: Metin içeriği
            
        Returns:
            {
                "valid": bool,
                "issues": List[str],
                "score": int (0-100),
                "warnings": List[str]
            }
        """
        issues = []
        warnings = []
        
        soru_text = question.get("soru_koku", "").lower()
        
        # 1. Numaralandırma kontrolü
        if "numaralanmış" in soru_text or "numaralandırıl" in soru_text:
            # Metinde gerçekten numaralandırma var mı?
            has_numbering = any(
                re.search(pattern, metin) 
                for pattern in self.DANGEROUS_PATTERNS["numaralanmış cümle"]
            )
            if not has_numbering:
                issues.append("❌ Soru 'numaralanmış cümle' istiyor ama metinde numaralandırma yok!")
        
        # 2. Boş şık kontrolü
        empty_options = []
        for key in ["sik_a", "sik_b", "sik_c", "sik_d"]:
            option = question.get(key, "").strip()
            # Sadece "I.", "II." gibi tek karakter/harf ise
            if len(option) < 5 or re.match(r'^[IVX]+\.?$', option) or re.match(r'^\d+\.?$', option):
                empty_options.append(key.upper().replace("SIK_", ""))
        
        if empty_options:
            issues.append(f"❌ Boş/çok kısa şıklar: {', '.join(empty_options)}")
        
        # 3. Alt konu uygunluğu
        required_keywords = self.SUBTOPIC_KEYWORDS.get(alt_konu, [])
        if required_keywords:
            # Soru metninde bu anahtar kelimelerin herhangi biri var mı?
            has_keyword = any(kw in soru_text for kw in required_keywords)
            if not has_keyword:
                issues.append(f"❌ Soru '{alt_konu}' konusuna uygun değil (anahtar kelime yok: {', '.join(required_keywords[:3])})")
        
        # 4. "Hangisi söylenemez" kontrolü (KALDIRILDI - çok sıkı)
        # Ana Düşünce sorularında "söylenemez" aslında kullanılabilir
        # if alt_konu == "Ana Düşünce" and "söylenemez" in soru_text:
        #     warnings.append("⚠️ Ana Düşünce sorularında 'söylenemez' kullanımı genelde uygun değil")
        
        # 5. Doğru cevap kontrolü
        correct = question.get("dogru_cevap", "").strip().upper()
        if correct not in ["A", "B", "C", "D"]:
            issues.append(f"❌ Geçersiz doğru cevap: {correct}")
        
        # 6. Şık uzunluk dengesi
        option_lengths = [
            len(question.get("sik_a", "")),
            len(question.get("sik_b", "")),
            len(question.get("sik_c", "")),
            len(question.get("sik_d", ""))
        ]
        if max(option_lengths) > 0:
            ratio = max(option_lengths) / max(min(option_lengths), 1)
            if ratio > 3:  # Bir şık diğerinden 3x uzunsa
                warnings.append(f"⚠️ Şık dengesi çok kötü (en uzun/en kısa oranı: {ratio:.1f})")
        
        # Skor hesapla
        score = 100
        score -= len(issues) * 30  # Her kritik hata -30 puan
        score -= len(warnings) * 10  # Her uyarı -10 puan
        score = max(0, score)
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": score
        }
    
    def get_validation_report(self, validation_result: Dict) -> str:
        """Validasyon sonucunu okunabilir rapor haline getirir."""
        report = []
        
        if validation_result["valid"]:
            report.append(f"✅ Soru geçerli (Skor: {validation_result['score']}/100)")
        else:
            report.append(f"❌ Soru geçersiz (Skor: {validation_result['score']}/100)")
        
        if validation_result["issues"]:
            report.append("\n**Kritik Sorunlar:**")
            for issue in validation_result["issues"]:
                report.append(f"  {issue}")
        
        if validation_result["warnings"]:
            report.append("\n**Uyarılar:**")
            for warning in validation_result["warnings"]:
                report.append(f"  {warning}")
        
        return "\n".join(report)


# Hızlı kullanım için fonksiyon
def validate_question(question: Dict, alt_konu: str, metin: str) -> Dict:
    """Soru doğrulaması yapar."""
    validator = QuestionValidator()
    return validator.validate(question, alt_konu, metin)
