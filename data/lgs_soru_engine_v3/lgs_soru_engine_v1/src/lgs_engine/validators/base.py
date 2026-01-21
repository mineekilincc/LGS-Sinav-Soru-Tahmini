from dataclasses import dataclass
from typing import Any, Dict, List, Optional

@dataclass
class ValidationResult:
    ok: bool
    score: float
    errors: List[str]

class Validator:
    def validate(self, q: Dict[str, Any]) -> ValidationResult:
        raise NotImplementedError
