from __future__ import annotations

import os
from dataclasses import dataclass

import requests
import base64


@dataclass(frozen=True)
class GeminiClient:
    api_key: str
    model: str = "gemini-2.5-flash"
    thinking_budget: int | None = 0  # 0 で thinking 無効（コスト/レイテンシ優先）

    def generate_text(
        self,
        *,
        system_instruction: str,
        user_text: str,
        response_mime_type: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        generation_config: dict[str, object] = {}
        if self.thinking_budget is not None:
            generation_config["thinkingConfig"] = {"thinkingBudget": int(self.thinking_budget)}
        if response_mime_type:
            generation_config["responseMimeType"] = response_mime_type
        if temperature is not None:
            generation_config["temperature"] = float(temperature)
        if max_output_tokens is not None:
            generation_config["maxOutputTokens"] = int(max_output_tokens)

        payload: dict[str, object] = {
            "system_instruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        }
        if generation_config:
            payload["generationConfig"] = generation_config

        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()

        # candidates[0].content.parts[*].text を結合
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini response has no candidates: {data}")
        content = (candidates[0] or {}).get("content") or {}
        parts = content.get("parts") or []
        texts: list[str] = []
        for p in parts:
            t = (p or {}).get("text")
            if isinstance(t, str):
                texts.append(t)
        return "".join(texts).strip()

    def generate_image(
        self,
        *,
        prompt: str,
        size: str = "1024x1024",
        image_format: str = "png",
    ) -> tuple[bytes, str]:
        """
        Generate an image from a text prompt using Google Generative Language API (Imagen/Image generation).

        Returns (image_bytes, mime_type).
        """
        url = "https://generativelanguage.googleapis.com/v1beta/models/imagegeneration:generate"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": {"text": prompt},
            # Common options; backend may accept width/height or size string
            "numberOfImages": 1,
            "size": size,
            "imageFormat": image_format.upper(),
        }
        r = requests.post(url, headers=headers, json=payload, timeout=90)
        r.raise_for_status()
        data = r.json()

        # Expected shape (subject to API evolution): candidates[0].image.imageBytes
        image_b64 = None
        mime = f"image/{image_format.lower()}"

        try:
            candidates = data.get("candidates") or []
            if candidates:
                image = (candidates[0] or {}).get("image") or {}
                image_b64 = image.get("imageBytes") or image.get("bytes")
                mime = image.get("mimeType") or mime
        except Exception:
            image_b64 = None

        # Fallbacks for alternative wire formats seen in samples
        if not image_b64:
            try:
                images = data.get("generatedImages") or []
                if images:
                    image = (images[0] or {}).get("image") or {}
                    image_b64 = image.get("base64") or image.get("imageBytes")
                    mime = image.get("mimeType") or mime
            except Exception:
                image_b64 = None

        if not image_b64:
            raise RuntimeError(f"Gemini image response missing bytes: {data}")

        try:
            raw = base64.b64decode(image_b64)
        except Exception as e:
            raise RuntimeError(f"Failed to decode image bytes: {type(e).__name__}") from e

        return raw, mime


def build_gemini_client() -> GeminiClient | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    model = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
    tb = os.environ.get("GEMINI_THINKING_BUDGET")
    thinking_budget: int | None
    if tb is None or tb == "":
        thinking_budget = 0
    elif tb.lower() in ("none", "null"):
        thinking_budget = None
    else:
        thinking_budget = int(tb)
    return GeminiClient(api_key=api_key, model=model, thinking_budget=thinking_budget)
