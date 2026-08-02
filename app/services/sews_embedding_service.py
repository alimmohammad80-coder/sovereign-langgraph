from __future__ import annotations

import os
from typing import Literal

from openai import OpenAI


MODEL = "nvidia/nemotron-3-embed-1b"
BASE_URL = "https://integrate.api.nvidia.com/v1"

EmbeddingInputType = Literal["passage", "query"]


class SEWSEmbeddingService:
    def __init__(self) -> None:
        api_key = (
            os.getenv("NVIDIA_API_KEY")
            or os.getenv("NVIDIA_NIM_API_KEY")
        )

        if not api_key:
            raise RuntimeError(
                "NVIDIA_API_KEY or NVIDIA_NIM_API_KEY "
                "must be configured."
            )

        self.client = OpenAI(
            api_key=api_key,
            base_url=BASE_URL,
        )

    def embed(
        self,
        text: str,
        *,
        input_type: EmbeddingInputType = "passage",
    ) -> list[float]:
        normalized = (text or "").strip()

        if not normalized:
            return []

        response = self.client.embeddings.create(
            model=MODEL,
            input=normalized,
            extra_body={
                "input_type": input_type,
                "modality": "text",
                "truncate": "END",
            },
        )

        vector = response.data[0].embedding

        if len(vector) != 2048:
            raise RuntimeError(
                "Unexpected NVIDIA embedding dimension: "
                f"{len(vector)}"
            )

        return vector
