from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelClient:
    """
    Üretici model ve judge model için tek istemci.

    - base_url: üretici model endpoint (generator)
    - judge_url: denetleyici model endpoint (judge) -> ayrı tutulması önerilir
    """

    base_url: Optional[str] = None
    judge_url: Optional[str] = None

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.4,
        top_p: float = 0.9,
        max_new_tokens: int = 800,
        repetition_penalty: float = 1.12,
    ) -> str:
        """
        Üretici modele istek atar.
        Bu repo iskeletinde gerçek HTTP çağrısı yok: kendi Colab/FastAPI inference'ına bağlamalısın.

        Beklenen: prompt -> raw string JSON
        """
        if not self.base_url:
            raise RuntimeError(
                "ModelClient.base_url tanımlı değil. "
                "Colab inference server URL'ini base_url olarak ver."
            )

        # TODO: Buraya gerçek HTTP POST ekle.
        # Şimdilik iskelet:
        raise NotImplementedError("generate(): HTTP entegrasyonu eklenmedi")

    def generate_judge(
        self,
        prompt: str,
        *,
        temperature: float = 0.2,
        top_p: float = 0.9,
        max_new_tokens: int = 300,
    ) -> str:
        """
        Judge modele istek atar.
        judge_url verilmezse base_url kullanır (fallback) ama önerilmez.
        """
        url = self.judge_url or self.base_url
        if not url:
            raise RuntimeError(
                "Judge icin judge_url veya base_url gerekli. "
                "Ayrı judge modeli önerilir (judge_url)."
            )

        # TODO: Buraya gerçek HTTP POST ekle.
        raise NotImplementedError("generate_judge(): HTTP entegrasyonu eklenmedi")
