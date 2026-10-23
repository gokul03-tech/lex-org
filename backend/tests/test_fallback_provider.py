"""Tests for the LLM fallback provider (primary -> backup failover)."""

from app.llm.fallback_provider import FallbackProvider


class FakeProvider:
    def __init__(self, model_id="fake", text="primary text", structured=None, raises=None):
        self.model_name = model_id
        self.model_id = model_id
        self.api_base = "http://primary"
        self.api_key = "k"
        self._text = text
        self._structured = structured if structured is not None else {"ok": True}
        self._raises = raises

    def generate(self, prompt, system_prompt="", max_tokens=2048, temperature=0.1, stop=None):
        if self._raises:
            raise self._raises
        return self._text

    def generate_structured(
        self, prompt, output_schema, system_prompt="", temperature=0.1, max_tokens=None
    ):
        if self._raises:
            raise self._raises
        return self._structured

    def stream_generate(self, prompt, system_prompt="", max_tokens=2048, temperature=0.1):
        if self._raises:
            raise self._raises
        yield "chunk"

    def generate_with_images(self, prompt, images, **kwargs):
        if self._raises:
            raise self._raises
        return "vision text"

    def get_model_info(self):
        return {"model_name": self.model_name}


def test_generate_falls_back_on_exception():
    provider = FallbackProvider(
        FakeProvider(text="", raises=RuntimeError("402")), FakeProvider(text="backup")
    )
    assert provider.generate("hi") == "backup"


def test_generate_falls_back_on_unavailable_sentinel():
    provider = FallbackProvider(
        FakeProvider(text="Model response unavailable for this analysis step."),
        FakeProvider(text="backup"),
    )
    assert provider.generate("hi") == "backup"


def test_generate_uses_primary_when_healthy():
    provider = FallbackProvider(FakeProvider(text="primary"), FakeProvider(text="backup"))
    assert provider.generate("hi") == "primary"


def test_structured_falls_back_on_error_dict():
    provider = FallbackProvider(
        FakeProvider(structured={"error": "402", "parse_error": True}),
        FakeProvider(structured={"ok": "backup"}),
    )
    assert provider.generate_structured("hi", {}) == {"ok": "backup"}


def test_structured_falls_back_on_exception():
    provider = FallbackProvider(
        FakeProvider(raises=RuntimeError("boom")), FakeProvider(structured={"ok": 1})
    )
    assert provider.generate_structured("hi", {}) == {"ok": 1}


def test_stream_falls_back():
    provider = FallbackProvider(
        FakeProvider(raises=RuntimeError("402")), FakeProvider()
    )
    assert list(provider.stream_generate("hi")) == ["chunk"]


def test_vision_falls_back():
    provider = FallbackProvider(
        FakeProvider(raises=RuntimeError("402")), FakeProvider()
    )
    assert provider.generate_with_images("read", [b"png"]) == "vision text"


def test_model_info_reports_both():
    info = FallbackProvider(FakeProvider("a"), FakeProvider("b")).get_model_info()
    assert info["primary"]["model_name"] == "a"
    assert info["fallback"]["model_name"] == "b"
