from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from lgs_engine.model.client import ModelClient
from lgs_engine.core.pipeline import GenerationPipeline
from lgs_engine.core.qtype_selector import QuestionTypeSelector


app = FastAPI(title="LGS Soru Engine")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Konu/kurallar dahil uretim istemi")
    n: int = Field(5, ge=1, le=20, description="Aday sayisi (rejection sampling)")
    mode: str = Field(
        "mixed",
        description="question_type secim modu: mixed | family | explicit_type",
    )
    topic_family: str | None = Field(
        None,
        description="mode=family iken kullanilir (Paragraf, Cumlede Anlam, Sozcukte Anlam, ...)"
    )
    question_type: str | None = Field(
        None,
        description="mode=explicit_type iken kullanilir (paragraf_ana_dusunce, cumlede_anlam_kosul, ...)"
    )
    seed: int | None = Field(None, description="Secim deterministik olsun istersen")


class GenerateResponse(BaseModel):
    selected_question_type: str
    question: dict


# NOTE: ModelClient stub; wire to your inference server
model = ModelClient(base_url=None)
selector = QuestionTypeSelector()
pipeline = GenerationPipeline(model, selector=selector)


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    qtype = selector.select(
        mode=req.mode,
        topic_family=req.topic_family,
        explicit_question_type=req.question_type,
        seed=req.seed,
    )

    # Prompt'u question_type ile kilitle.
    # (Fine-tune'da bu satiri gorup tip davranisini oturtuyoruz.)
    wrapped_prompt = f"Soru tipi: {qtype}\n{req.prompt.strip()}"

    q = pipeline.generate_best(wrapped_prompt, n=req.n, expected_question_type=qtype)
    return {"selected_question_type": qtype, "question": q}
