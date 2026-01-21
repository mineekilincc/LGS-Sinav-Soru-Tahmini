from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .base import Validator, ValidationResult
from ..utils.text import (
    highlight_appears_in_text,
    sentence_count,
    word_count,
)


@dataclass(frozen=True)
class TypeContract:
    defaults: Dict[str, Any]
    rules: Dict[str, Dict[str, Any]]

    @staticmethod
    def load(path: Path) -> "TypeContract":
        obj = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        defaults = obj.get("defaults", {}) or {}
        rules = obj.get("rules", {}) or {}
        return TypeContract(defaults=defaults, rules=rules)


class TypeRuleValidator(Validator):
    """Question-type sözleşmesini uygular.

    Bu validator, şu sınıf hataları yakalamak için tasarlanmıştır:
    - Cümlede anlam gibi tiplerde paragraf üretimi (çok cümle/çok kelime)
    - Paragraf tiplerinde aşırı kısa/uzun metin
    - Underline (highlight) istenip üretilmemesi
    - topic_family uyuşmazlığı (kısmi)
    """

    def __init__(self, contract_path: Optional[Path] = None):
        if contract_path is None:
            contract_path = Path(__file__).resolve().parents[3] / "configs" / "question_type_rules.yaml"
        self.contract_path = contract_path
        self.contract = TypeContract.load(contract_path)

    def _rule(self, qtype: str) -> Optional[Dict[str, Any]]:
        return self.contract.rules.get(qtype)

    def validate(self, q: Dict[str, Any]) -> ValidationResult:
        qt = str(q.get("question_type", "")).strip()
        rules = self._rule(qt)
        if not rules:
            # Bilinmeyen tip: soft-pass. Pipeline yine de HardValidator ile korunur.
            return ValidationResult(True, 0.5, ["unknown_question_type"])

        errors: list[str] = []
        txt = str(q.get("text", "") or "")
        wc = word_count(txt)
        sc = sentence_count(txt)

        # topic_family uyumu (varsa)
        expected_family = rules.get("topic_family")
        if expected_family:
            actual_family = str(q.get("topic_family", "")).strip()
            if actual_family and actual_family != expected_family:
                errors.append("topic_family_mismatch")

        # text_required
        text_required = bool(rules.get("text_required", True))
        if text_required and not txt.strip() and self.contract.defaults.get("reject_if_text_empty_when_required", True):
            errors.append("text_required_but_empty")

        # word limits
        if "min_words" in rules and wc < int(rules["min_words"]):
            errors.append("text_too_short")
        if "max_words" in rules and wc > int(rules["max_words"]):
            errors.append("text_too_long")

        # sentence limits
        if "min_sentences" in rules and sc < int(rules["min_sentences"]):
            errors.append("too_few_sentences")
        if "max_sentences" in rules and sc > int(rules["max_sentences"]):
            errors.append("too_many_sentences")

        # highlight rules
        highlight_required = bool(rules.get("highlight_required", False))
        highlight = q.get("highlight")
        highlight_text = "" if highlight is None else str(highlight).strip()

        if highlight_required and not highlight_text:
            errors.append("highlight_required")

        if highlight_text:
            # highlight kelime sayisi
            hw = word_count(highlight_text)
            if "highlight_min_words" in rules and hw < int(rules["highlight_min_words"]):
                errors.append("highlight_too_short")
            if "highlight_max_words" in rules and hw > int(rules["highlight_max_words"]):
                errors.append("highlight_too_long")

            if self.contract.defaults.get("highlight_must_appear_in_text", True):
                if not highlight_appears_in_text(txt, highlight_text):
                    errors.append("highlight_not_in_text")

        ok = len(errors) == 0
        score = 1.0 if ok else 0.0
        return ValidationResult(ok, score, errors)
