from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass(frozen=True)
class _RulesIndex:
    all_types: List[str]
    by_family: Dict[str, List[str]]


class QuestionTypeSelector:
    """question_type secimi.

    Amac:
    - UI alt konu listesini zorunlu kilmadan (mixed) saglam bir tip secimi yapmak
    - Istenirse sadece topic_family icinden secmek (family)
    - Istenirse dogrudan tip kilitlemek (explicit_type)
    """

    def __init__(self, contract_path: Optional[Path] = None):
        if contract_path is None:
            contract_path = Path(__file__).resolve().parents[3] / "configs" / "question_type_rules.yaml"
        self.contract_path = contract_path
        self._index = self._build_index()

    def _build_index(self) -> _RulesIndex:
        obj = yaml.safe_load(self.contract_path.read_text(encoding="utf-8")) or {}
        rules = obj.get("rules", {}) or {}

        by_family: Dict[str, List[str]] = {}
        all_types: List[str] = []

        for qtype, r in rules.items():
            all_types.append(qtype)
            fam = str(r.get("topic_family", "")).strip()
            if fam:
                by_family.setdefault(fam, []).append(qtype)

        # stabil order
        all_types.sort()
        for fam in list(by_family.keys()):
            by_family[fam].sort()

        return _RulesIndex(all_types=all_types, by_family=by_family)

    def available_families(self) -> List[str]:
        return sorted(self._index.by_family.keys())

    def available_types(self, *, topic_family: Optional[str] = None) -> List[str]:
        if topic_family:
            return list(self._index.by_family.get(topic_family, []))
        return list(self._index.all_types)

    def select(
        self,
        *,
        mode: str = "mixed",
        topic_family: Optional[str] = None,
        explicit_question_type: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> str:
        """Secim yapar.

        mode:
          - mixed: tum tiplerden sec
          - family: sadece topic_family icinden sec
          - explicit_type: explicit_question_type'i kullan
        """

        mode = (mode or "mixed").strip().lower()

        if mode == "explicit_type":
            if not explicit_question_type:
                raise ValueError("mode=explicit_type icin question_type gerekli")
            if explicit_question_type not in self._index.all_types:
                raise ValueError(f"Bilinmeyen question_type: {explicit_question_type}")
            return explicit_question_type

        rng = random.Random(seed) if seed is not None else random

        if mode == "family":
            if not topic_family:
                raise ValueError("mode=family icin topic_family gerekli")
            candidates = self._index.by_family.get(topic_family, [])
            if not candidates:
                raise ValueError(f"topic_family icin hic question_type yok: {topic_family}")
            return rng.choice(candidates)

        # mixed
        return rng.choice(self._index.all_types)
