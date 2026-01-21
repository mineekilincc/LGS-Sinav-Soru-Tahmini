from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SemanticResult:
    ok: bool
    errors: List[str]
    score: float
    judge_payload: Optional[Dict[str, Any]] = None


class SemanticJudge:
    """
    LLM-judge tabanlı semantik kontrol.

    Yenilik:
    - Ayrı judge endpoint'i destekler: model_client.generate_judge()
    - generate_judge yoksa fallback: model_client.generate (önerilmez ama çalışır)

    Kontroller:
    - Tek doğru cevap (solver-check)
    - Tip/Konu uyumu (alignment 0-10)
    - Eminlik (confidence 0-1)
    """

    def __init__(
        self,
        model_client,
        *,
        min_confidence: float = 0.55,
        min_alignment: float = 6.0,  # 0-10
    ):
        self.model = model_client
        self.min_confidence = min_confidence
        self.min_alignment = min_alignment

    def evaluate(
        self,
        q: Dict[str, Any],
        *,
        expected_question_type: Optional[str] = None,
        expected_topic_family: Optional[str] = None,
    ) -> SemanticResult:
        errors: List[str] = []

        payload = self._judge(q, expected_question_type, expected_topic_family)
        if not payload:
            return SemanticResult(ok=False, errors=["judge_no_response"], score=0.0, judge_payload=None)

        predicted = str(payload.get("predicted_answer", "")).strip().upper()
        conf = self._to_float(payload.get("confidence"), default=0.0)
        align = self._to_float(payload.get("alignment"), default=0.0)

        true_ans = str(q.get("dogru_cevap", "")).strip().upper()

        if predicted not in {"A", "B", "C", "D"}:
            errors.append("judge_invalid_predicted_answer")

        if predicted in {"A", "B", "C", "D"} and true_ans in {"A", "B", "C", "D"}:
            if predicted != true_ans:
                errors.append("solver_mismatch")

        if conf < self.min_confidence:
            errors.append("low_confidence")

        if align < self.min_alignment:
            errors.append("low_alignment")

        ok = len(errors) == 0
        score = 1.0 if ok else 0.0
        return SemanticResult(ok=ok, errors=errors, score=score, judge_payload=payload)

    def _judge(
        self,
        q: Dict[str, Any],
        expected_question_type: Optional[str],
        expected_topic_family: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        meta_lines = []
        if expected_topic_family:
            meta_lines.append(f"- Beklenen konu ailesi: {expected_topic_family}")
        if expected_question_type:
            meta_lines.append(f"- Beklenen soru tipi: {expected_question_type}")
        meta = "\n".join(meta_lines) if meta_lines else "- Beklenen tip: (belirtilmedi)"

        question_json = {
            "question_type": q.get("question_type"),
            "metin": q.get("metin", ""),
            "highlight": q.get("highlight", q.get("vurgulu_ifade", "")),
            "soru": q.get("soru", ""),
            "sik_a": q.get("sik_a", ""),
            "sik_b": q.get("sik_b", ""),
            "sik_c": q.get("sik_c", ""),
            "sik_d": q.get("sik_d", ""),
            "dogru_cevap": q.get("dogru_cevap", ""),
        }

        prompt = (
            "Sen bir LGS Türkçe soru denetçisisin.\n"
            "Görevlerin:\n"
            "1) Soruyu çöz ve doğru şıkkı (A/B/C/D) tahmin et.\n"
            "2) Sorunun beklenen konu/tip ile uyumunu 0-10 arası puanla.\n"
            "3) Eminlik (confidence) 0-1 arası ver.\n\n"
            f"{meta}\n\n"
            "SADECE şu JSON şemasıyla cevap ver:\n"
            '{"predicted_answer":"A","confidence":0.0,"alignment":0.0,"notes":"kisa"}\n\n'
            "Soru JSON:\n"
            f"{json.dumps(question_json, ensure_ascii=False)}"
        )

        try:
            if hasattr(self.model, "generate_judge"):
                raw = self.model.generate_judge(
                    prompt,
                    temperature=0.2,
                    top_p=0.9,
                    max_new_tokens=250,
                )
            else:
                # fallback (önerilmez)
                raw = self.model.generate(
                    prompt,
                    temperature=0.2,
                    top_p=0.9,
                    max_new_tokens=250,
                )
        except Exception:
            return None

        return self._try_parse_json(raw)

    def _try_parse_json(self, s: str) -> Optional[Dict[str, Any]]:
        s = (s or "").strip()
        if "{" in s and "}" in s:
            s = s[s.find("{") : s.rfind("}") + 1]
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                return obj
        except Exception:
            return None
        return None

    def _to_float(self, x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default
