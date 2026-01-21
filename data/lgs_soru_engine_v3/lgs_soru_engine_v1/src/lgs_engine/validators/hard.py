from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import re


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str]
    score: float


class HardValidator:
    """
    Hard (kati) kurallar:
    - JSON anahtarları var mı?
    - Şıklar ve doğru cevap geçerli mi?
    - Aşırı tekrar / loop var mı?
    - Çok kısa / boş alanlar var mı?
    """

    REQUIRED_KEYS = ["soru", "sik_a", "sik_b", "sik_c", "sik_d", "dogru_cevap", "question_type"]
    CHOICE_KEYS = ["sik_a", "sik_b", "sik_c", "sik_d"]
    VALID_ANSWERS = {"A", "B", "C", "D"}

    def validate(self, q: Dict[str, Any]) -> ValidationResult:
        errors: List[str] = []
        score = 0.0

        # 1) Required keys
        for k in self.REQUIRED_KEYS:
            if k not in q:
                errors.append(f"missing_{k}")

        if errors:
            return ValidationResult(ok=False, errors=errors, score=0.0)

        # 2) Answer validity
        ans = str(q.get("dogru_cevap", "")).strip().upper()
        if ans not in self.VALID_ANSWERS:
            errors.append("invalid_answer_letter")

        # 3) Choice fields non-empty + not too short
        choices = []
        for k in self.CHOICE_KEYS:
            v = str(q.get(k, "")).strip()
            if not v:
                errors.append(f"empty_{k}")
            choices.append(v)

        # 4) Duplicate / near-duplicate choices
        norm_choices = [self._normalize_text(c) for c in choices]
        if len(set(norm_choices)) < 4:
            errors.append("duplicate_choices")

        # 5) Very short stem check
        stem = str(q.get("soru", "")).strip()
        if len(stem) < 15:
            errors.append("stem_too_short")

        # 6) Optional text sanity (if provided)
        text = str(q.get("metin", "") or "").strip()
        if "metin" in q:
            # metin alanı varsa aşırı kısa/boş ise sinyal (hard değil bazı tiplerde)
            if text and len(text) < 30:
                errors.append("text_too_short")

        # 7) Loop / repetition detection (text + stem)
        if self._has_repetition_loop(text):
            errors.append("text_repetition_loop")
        if self._has_repetition_loop(stem):
            errors.append("stem_repetition_loop")

        # 8) Basic profanity / obvious garbage token patterns (very light)
        # (Bu bir dil filtresi değil; sadece aşırı bozuk üretimleri yakalar.)
        if self._looks_like_garbage(text) or self._looks_like_garbage(stem):
            errors.append("garbage_tokens")

        ok = len(errors) == 0
        if ok:
            score = 1.0
        return ValidationResult(ok=ok, errors=errors, score=score)

    def _normalize_text(self, s: str) -> str:
        s = s.strip().lower()
        s = re.sub(r"\s+", " ", s)
        s = re.sub(r"[^\wçğıöşüâîû\s]", "", s)
        return s

    def _split_sentences(self, s: str) -> List[str]:
        s = s.strip()
        if not s:
            return []
        # Basit cümle bölme
        parts = re.split(r"(?<=[.!?])\s+", s)
        parts = [p.strip() for p in parts if p.strip()]
        return parts

    def _has_repetition_loop(self, s: str) -> bool:
        """
        Loop sinyalleri:
        - Aynı cümle ardışık tekrar (2+)
        - Son 3 cümlede aynı cümle tekrar
        """
        sentences = self._split_sentences(s)
        if len(sentences) < 3:
            return False

        norm = [self._normalize_text(x) for x in sentences]

        # ardışık tekrar
        for i in range(1, len(norm)):
            if norm[i] and norm[i] == norm[i - 1]:
                return True

        # son 3'te tekrar
        tail = norm[-3:]
        if len(set(tail)) < len(tail):
            return True

        # aynı cümle 3+ kez geçiyorsa
        freq: Dict[str, int] = {}
        for n in norm:
            if not n:
                continue
            freq[n] = freq.get(n, 0) + 1
            if freq[n] >= 3:
                return True

        return False

    def _looks_like_garbage(self, s: str) -> bool:
        if not s:
            return False
        # aşırı ardışık aynı karakter
        if re.search(r"(.)\1\1\1\1", s):
            return True
        # çok fazla sembol
        non_word = sum(1 for ch in s if not ch.isalnum() and not ch.isspace())
        if len(s) > 0 and (non_word / max(1, len(s))) > 0.25:
            return True
        return False
