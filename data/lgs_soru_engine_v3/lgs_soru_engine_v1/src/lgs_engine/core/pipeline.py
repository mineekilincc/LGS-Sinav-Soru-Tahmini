from __future__ import annotations

import json
from typing import Any, Dict, Optional

from ..model.client import ModelClient
from ..validators.hard import HardValidator
from ..validators.type_rules import TypeRuleValidator
from ..validators.semantic_judge import SemanticJudge
from .qtype_selector import QuestionTypeSelector
from .telemetry import Telemetry


class GenerationPipeline:
    def __init__(
        self,
        model: ModelClient,
        *,
        selector: Optional[QuestionTypeSelector] = None,
        enable_semantic_judge: bool = True,
        judge_min_confidence: float = 0.55,
        judge_min_alignment: float = 6.0,
        telemetry: Optional[Telemetry] = None,
    ):
        self.model = model
        self.selector = selector
        self.hard = HardValidator()
        self.typev = TypeRuleValidator()
        self.semantic = SemanticJudge(
            model,
            min_confidence=judge_min_confidence,
            min_alignment=judge_min_alignment,
        )
        self.enable_semantic_judge = enable_semantic_judge
        self.telemetry = telemetry or Telemetry.default()

    def _try_parse(self, s: str) -> Optional[Dict[str, Any]]:
        s = s.strip()
        if "{" in s and "}" in s:
            s = s[s.find("{") : s.rfind("}") + 1]
        try:
            return json.loads(s)
        except Exception:
            return None

    def _repair_to_json(self, raw: str, prompt: str) -> Optional[Dict[str, Any]]:
        repair_prompt = (
            "Aşağıdaki metni SADECE geçerli JSON olacak şekilde düzelt. "
            "JSON dışında hiçbir açıklama yazma.\n\n"
            f"METIN:\n{raw}\n"
        )
        try:
            repaired = self.model.generate(
                repair_prompt,
                temperature=0.2,
                top_p=0.9,
                max_new_tokens=500,
            )
        except Exception:
            self.telemetry.log(stage="json_repair_exception", prompt=prompt, raw=raw)
            return None

        obj = self._try_parse(repaired)
        if not obj:
            self.telemetry.log(stage="json_repair_failed", prompt=prompt, raw=repaired)
        return obj

    def _repair_highlight(self, q: Dict[str, Any], prompt: str) -> Optional[Dict[str, Any]]:
        j = json.dumps(q, ensure_ascii=False)
        repair_prompt = (
            "Aşağıdaki JSON bir LGS sorusudur. SADECE JSON döndür. "
            "Hedef: underline/altı çizili gereksinimini düzelt.\n"
            "Kurallar:\n"
            "- JSON şemasını bozma, anahtarları değiştirme.\n"
            "- Eğer highlight boşsa, text içinden 3-8 kelimelik bir ifadeyi highlight olarak seç.\n"
            "- highlight text içinde birebir geçmek zorunda.\n"
            "- text içinde highlight'ın geçtiği ilk yeri [u]...[/u] ile işaretle.\n"
            "- SADECE JSON.\n\n"
            f"JSON:\n{j}"
        )
        try:
            repaired = self.model.generate(
                repair_prompt,
                temperature=0.2,
                top_p=0.9,
                max_new_tokens=700,
            )
        except Exception:
            self.telemetry.log(stage="highlight_repair_exception", prompt=prompt, parsed=q)
            return None

        obj = self._try_parse(repaired)
        if not obj:
            self.telemetry.log(stage="highlight_repair_failed", prompt=prompt, raw=repaired)
        return obj

    def generate_best(
        self,
        prompt: str,
        n: int = 5,
        *,
        expected_question_type: Optional[str] = None,
        expected_topic_family: Optional[str] = None,
    ) -> Dict[str, Any]:
        best: Optional[Dict[str, Any]] = None
        best_score = -1.0

        for _ in range(max(1, n)):
            # 1) üret
            try:
                raw = self.model.generate(prompt)
            except Exception:
                self.telemetry.log(stage="generate_exception", prompt=prompt)
                continue

            # 2) parse / repair
            obj = self._try_parse(raw)
            if not obj:
                self.telemetry.log(stage="json_parse_failed", prompt=prompt, raw=raw)
                obj = self._repair_to_json(raw, prompt)
                if not obj:
                    continue

            # 3) type kilidi
            if expected_question_type:
                obj["question_type"] = expected_question_type

            # 4) hard + type
            h = self.hard.validate(obj)
            if not h.ok:
                self.telemetry.log(stage="hard_fail", prompt=prompt, parsed=obj, errors=h.errors)
                continue

            t = self.typev.validate(obj)
            if not t.ok:
                # highlight özel repair
                if any(e in {"highlight_required", "highlight_not_in_text"} for e in t.errors):
                    repaired = self._repair_highlight(obj, prompt)
                    if repaired:
                        if expected_question_type:
                            repaired["question_type"] = expected_question_type
                        h2 = self.hard.validate(repaired)
                        t2 = self.typev.validate(repaired)
                        if h2.ok and t2.ok:
                            obj = repaired
                            h = h2
                            t = t2
                        else:
                            self.telemetry.log(
                                stage="type_fail_after_highlight_repair",
                                prompt=prompt,
                                parsed=repaired,
                                errors=(h2.errors + t2.errors),
                            )
                            continue
                    else:
                        self.telemetry.log(stage="type_fail_highlight_repair_unavailable", prompt=prompt, parsed=obj, errors=t.errors)
                        continue
                else:
                    self.telemetry.log(stage="type_fail", prompt=prompt, parsed=obj, errors=t.errors)
                    continue

            # 5) semantic judge (ayrı judge ile)
            sem_score = 1.0
            if self.enable_semantic_judge:
                sem = self.semantic.evaluate(
                    obj,
                    expected_question_type=expected_question_type,
                    expected_topic_family=expected_topic_family,
                )
                if not sem.ok:
                    self.telemetry.log(
                        stage="semantic_fail",
                        prompt=prompt,
                        parsed=obj,
                        errors=sem.errors,
                        extra={"judge_payload": sem.judge_payload},
                    )
                    continue
                sem_score = sem.score

            score = float(h.score) + float(t.score) + float(sem_score)
            if score > best_score:
                best_score = score
                best = obj

        if not best:
            raise ValueError("No valid candidate produced")
        return best
