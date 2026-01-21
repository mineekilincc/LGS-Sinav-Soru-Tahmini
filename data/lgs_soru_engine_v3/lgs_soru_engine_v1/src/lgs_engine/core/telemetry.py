from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class Telemetry:
    """
    Active learning / hard-negative log.

    Amaç:
    - Üretimde elenen adayları nedenleriyle kaydetmek
    - Sonraki fine-tune için "negative training" havuzu oluşturmak
    """

    out_path: Path

    @classmethod
    def default(cls) -> "Telemetry":
        # repo kökü: .../src/lgs_engine/core/telemetry.py -> parents[3] projeye denk gelir
        root = Path(__file__).resolve().parents[3]
        data_dir = root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return cls(out_path=data_dir / "hard_negatives.jsonl")

    def log(
        self,
        *,
        stage: str,
        prompt: str,
        raw: Optional[str] = None,
        parsed: Optional[Dict[str, Any]] = None,
        errors: Optional[list[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        rec: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "prompt": prompt,
        }
        if raw is not None:
            rec["raw"] = raw
        if parsed is not None:
            rec["parsed"] = parsed
        if errors is not None:
            rec["errors"] = errors
        if extra is not None:
            rec["extra"] = extra

        with self.out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
