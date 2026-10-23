"""Tests for the vision-LLM OCR fallback (OpenRouter multimodal).

Rendering is monkeypatched so the tests need no real PDF or GPU, and a fake
provider keeps them offline and deterministic.
"""

import base64

from app.document_pipeline import vlm_ocr
from app.document_pipeline.vlm_ocr import garbage_ratio, needs_vlm_ocr, vlm_ocr_fallback
from app.llm.openai_compatible_provider import OpenAICompatibleProvider


def test_garbage_ratio_and_quality_gate():
    assert garbage_ratio("") == 1.0
    assert garbage_ratio("The petition is allowed under Section 439.") < 0.15
    assert garbage_ratio("\ufffd\ufffd\ufffd\ufffd\x00\x01\x02\x03") > 0.5
    assert needs_vlm_ocr("") is True
    assert needs_vlm_ocr("too short") is True
    assert needs_vlm_ocr("The said bail petition is allowed by this Court. " * 20) is False


class FakeVisionProvider:
    def __init__(self, text="clean extracted text", raises=None):
        self.text = text
        self.raises = raises
        self.calls = []

    def generate_with_images(self, prompt, images, **kwargs):
        self.calls.append((prompt, images, kwargs))
        if self.raises:
            raise self.raises
        return self.text


class NoVisionProvider:
    def generate(self, *_a, **_k):
        return "text only"


def test_vlm_ocr_fallback_reads_pages(monkeypatch):
    monkeypatch.setattr(vlm_ocr.settings, "VLM_OCR_ENABLED", True)
    monkeypatch.setattr(vlm_ocr, "_render_pdf_pages", lambda *a, **k: [b"PNG1", b"PNG2"])
    provider = FakeVisionProvider(text="IN THE HIGH COURT ... petition allowed")
    out = vlm_ocr_fallback("scan.pdf", provider, max_pages=5)
    assert out == "IN THE HIGH COURT ... petition allowed"
    assert len(provider.calls[0][1]) == 2


def test_vlm_ocr_fallback_empty_when_provider_cannot_see(monkeypatch):
    monkeypatch.setattr(vlm_ocr.settings, "VLM_OCR_ENABLED", True)
    monkeypatch.setattr(vlm_ocr, "_render_pdf_pages", lambda *a, **k: [b"PNG"])
    assert vlm_ocr_fallback("scan.pdf", NoVisionProvider()) == ""


def test_vlm_ocr_fallback_degrades_on_error(monkeypatch):
    monkeypatch.setattr(vlm_ocr.settings, "VLM_OCR_ENABLED", True)
    monkeypatch.setattr(vlm_ocr, "_render_pdf_pages", lambda *a, **k: [b"PNG"])
    provider = FakeVisionProvider(raises=RuntimeError("model down"))
    assert vlm_ocr_fallback("scan.pdf", provider) == ""


def test_vlm_ocr_fallback_disabled(monkeypatch, settings_override=None):
    monkeypatch.setattr(vlm_ocr.settings, "VLM_OCR_ENABLED", False)
    assert vlm_ocr_fallback("scan.pdf", FakeVisionProvider()) == ""


class _FakeResponse:
    def __init__(self, content):
        self.content = content
        self.status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


def test_provider_generate_with_images_builds_data_uri_payload(monkeypatch):
    provider = OpenAICompatibleProvider(
        model_name="vision",
        api_base="https://openrouter.ai/api/v1",
        api_key="k",
        model_id="google/gemini-2.5-flash",
    )
    captured = {}

    def fake_post(payload, headers, **_kwargs):
        captured["payload"] = payload
        return _FakeResponse("digitized text")

    monkeypatch.setattr(provider, "_post_with_backoff", fake_post)
    out = provider.generate_with_images("read this", [b"\x89PNG"], max_tokens=100)

    assert out == "digitized text"
    content = captured["payload"]["messages"][-1]["content"]
    assert content[0] == {"type": "text", "text": "read this"}
    url = content[1]["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
    assert base64.b64decode(url.split(",", 1)[1]) == b"\x89PNG"


def test_vision_role_maps_to_vlm_model(monkeypatch):
    from app.core.config import settings as app_settings
    from app.llm import provider as provider_mod

    monkeypatch.setattr(app_settings, "VLM_OCR_MODEL", "some/vision-model")
    monkeypatch.setattr(app_settings, "GEMINI_API_KEY", "")
    prov = provider_mod.get_llm_provider("vision")
    assert prov.model_id == "some/vision-model"
