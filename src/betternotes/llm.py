"""KI-Wrapper. Kapselt Google Gemini hinter zwei einfachen Methoden, damit die
übrigen Module (extract, summarize, news) anbieterunabhängig bleiben und in Tests
leicht ersetzt werden können.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, api_key: str, model: str):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self.model = model

    def _config(self, system: str, max_tokens: int):
        from google.genai import types

        return types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        )

    def complete(self, system: str, prompt: str, max_tokens: int = 2048) -> str:
        """Reine Textantwort auf einen Prompt."""
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self._config(system, max_tokens),
        )
        return (response.text or "").strip()

    def transcribe(
        self, images: list[bytes], system: str, prompt: str, max_tokens: int = 4096
    ) -> str:
        """Bilder (PNG) + Anweisung -> Text (OCR/Transkription)."""
        from google.genai import types

        parts = [types.Part.from_bytes(data=png, mime_type="image/png") for png in images]
        parts.append(types.Part.from_text(text=prompt))
        response = self._client.models.generate_content(
            model=self.model,
            contents=parts,
            config=self._config(system, max_tokens),
        )
        return (response.text or "").strip()
