

"""Llama.cpp GGUF LLM provider for local quantized model inference.

Requires llama-cpp-python package. Falls back to MockProvider if not installed.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from loguru import logger

from app.llm.provider import LLMProvider

# Module-level shared Llama instances so every provider instantiation
# reuses the same loaded weights instead of re-mmapping the GGUF per agent.
_shared_llamas: dict[tuple, Any] = {}
_load_lock = threading.Lock()


_cuda_check: dict[str, bool] = {}


def _cuda_available() -> bool:
    """True only when llama-cpp was built with a usable CUDA backend.

    A CPU-only build silently ignores n_gpu_layers, so setting the env var alone
    appears to do nothing. This detects that case and says so plainly instead of
    leaving the configuration looking applied. Memoised because the probe prints
    a device banner on every call.
    """
    cached = _cuda_check.get("ok")
    if cached is not None:
        return cached
    try:
        from llama_cpp import llama_cpp as _lc

        has_cuda = bool(getattr(_lc, "llama_supports_gpu_offload", lambda: False)())
    except Exception:
        has_cuda = False
    _cuda_check["ok"] = has_cuda
    return has_cuda


def _gpu_memory_by_pid() -> set[int]:
    """PIDs of processes currently holding GPU memory."""
    try:
        import subprocess

        out = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        return {int(x) for x in out.stdout.split() if x.strip().isdigit()}
    except Exception:
        return set()


def _free_vram_mb() -> float:
    """VRAM not in use by anyone.

    Memory held by ANOTHER process on the same GPU is not ours to allocate. A
    long-running uvicorn that already holds the model still leaves enough
    headroom, but a second concurrent run does not - which previously made the
    provider pick 0 layers, fail to create a llama_context, and thrash through
    its retry ladder.
    """
    try:
        import subprocess

        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        return float(out.stdout.strip().splitlines()[0])
    except Exception:
        return 0.0


_auto_layers_cache: dict[tuple, int] = {}


def _auto_gpu_layers(model_path: str, requested: int, n_ctx: int) -> int:
    """Choose a layer count that fits the GPU instead of guessing.

    A partial offload fails at load time with a CUDA OOM, and the failure mode is
    slow and confusing. Budget = free VRAM - KV cache - ~350MB CUDA context, then
    convert that to layers from the model's own file size. On a 4GB card with a
    4.7GB model this yields a usable partial offload instead of asking for all
    layers and dying.

    The result is memoised per (model, requested, n_ctx). Without this the answer
    changes as transient VRAM use rises and falls, which also changes the
    shared-model cache key - so the same model was re-mapped from disk on every
    agent (observed: 21 reloads in one run, 0 MiB actually resident on the GPU).
    """
    if requested <= 0:
        return 0
    cache_key = (model_path, requested, n_ctx)
    if cache_key in _auto_layers_cache:
        return _auto_layers_cache[cache_key]
    result = _auto_gpu_layers_measure(model_path, requested, n_ctx)
    _auto_layers_cache[cache_key] = result
    return result


def _auto_gpu_layers_measure(model_path: str, requested: int, n_ctx: int) -> int:
    """Choose a layer count that fits the GPU instead of guessing.

    A partial offload fails at load time with a CUDA OOM, and the failure mode is
    slow and confusing. Budget = free VRAM - KV cache - ~350MB CUDA context, then
    convert that to layers from the model's own file size. On a 4GB card with a
    4.7GB model this yields a usable partial offload instead of asking for all
    layers and dying.
    """
    if requested <= 0:
        return 0
    free_mb = _free_vram_mb()

    if free_mb <= 0:
        logger.warning("No free VRAM detected; running the model on CPU.")
        return 0

    # KV cache estimate (GQA, f32) plus CUDA context/workspace headroom.
    layers, kv_heads, head_dim = 28, 4, 128
    kv_mb = 2 * layers * kv_heads * head_dim * max(512, n_ctx) * 4 / 1e6
    budget_mb = free_mb - kv_mb - 350
    if budget_mb <= 200:
        logger.warning(
            f"Only {free_mb:.0f}MB free VRAM; not enough for GPU offload. Using CPU."
        )
        return 0

    try:
        weight_mb = os.path.getsize(model_path) / 1e6
        total_layers = 28
        affordable = int(budget_mb / (weight_mb / total_layers))
        chosen = max(0, min(requested, affordable, total_layers))
    except Exception:
        chosen = requested

    holders = _gpu_memory_by_pid()
    if chosen == 0:
        if holders:
            logger.warning(
                f"Only {free_mb:.0f}MB VRAM free and it is held by process(es) "
                f"{sorted(holders)}; not enough for this process. Using CPU. "
                f"Stop the other process (or raise LLM_N_GPU_LAYERS) to use the GPU."
            )
        else:
            logger.warning("Not enough VRAM for any layer; falling back to CPU.")
    elif chosen < requested:
        logger.info(
            f"VRAM budget: {free_mb:.0f}MB free, KV ~{kv_mb:.0f}MB -> "
            f"offloading {chosen}/{total_layers} layers (requested {requested})."
        )
    return chosen


_MOCK_FALLBACK_ACTIVE = False
_MOCK_FALLBACK_WARNED = False


def is_mock_fallback_active() -> bool:
    """True when any generation in this process was served by MockProvider.

    Callers surface this on the case record: without it a failed model load
    yields fluent, entirely invented analysis that looks like a real result.
    """
    return _MOCK_FALLBACK_ACTIVE


def reset_mock_fallback() -> None:
    global _MOCK_FALLBACK_ACTIVE, _MOCK_FALLBACK_WARNED
    _MOCK_FALLBACK_ACTIVE = False
    _MOCK_FALLBACK_WARNED = False


def _warn_mock_once(op: str) -> None:
    """Emit one unmissable warning per process, not one per call."""
    global _MOCK_FALLBACK_WARNED
    if _MOCK_FALLBACK_WARNED:
        return
    _MOCK_FALLBACK_WARNED = True
    logger.error(
        "LLM UNAVAILABLE - returning MOCK output for {op}. Every LLM-generated "
        "field in this run is synthetic, not analysed. This usually means the "
        "GGUF could not be allocated (another process holds the GPU/RAM, or "
        "LLM_N_GPU_LAYERS exceeds free VRAM). Stop the other process or lower "
        "LLM_N_GPU_LAYERS; the case record is now flagged as degraded.".format(op=op)
    )


_shared_llm = None


def _get_shared_llama(model_path: str, n_ctx: int = 2048, n_threads: int = 4, n_gpu_layers: int = 15):
    """Load (once) and return a shared Llama instance for the given config."""
    global _shared_llm
    if _shared_llm is not None:
        return _shared_llm
    key = (model_path, n_ctx, n_threads, n_gpu_layers)
    with _load_lock:
        if _shared_llm is not None:
            return _shared_llm
        if key in _shared_llamas:
            _shared_llm = _shared_llamas[key]
            return _shared_llm
        from llama_cpp import Llama

        logger.info(f"Loading GGUF model from {model_path} (n_gpu_layers={n_gpu_layers}, n_ctx={n_ctx})")
        try:
            model = Llama(
                model_path=model_path,
                n_ctx=min(n_ctx, 2048),
                n_threads=n_threads,
                n_gpu_layers=n_gpu_layers,
                enable_thinking=False,
                verbose=False,
                use_mmap=True,
                use_mlock=True,  # CRITICAL: Prevent swapping
                n_batch=512,
            )
            logger.info("Model ready: qwen-gguf (mlock enabled)")
        except Exception as exc:
            logger.warning(f"Failed loading with use_mlock=True or n_gpu_layers={n_gpu_layers}: {exc}. Retrying with use_mlock=False...")
            try:
                model = Llama(
                    model_path=model_path,
                    n_ctx=min(n_ctx, 2048),
                    n_threads=n_threads,
                    n_gpu_layers=n_gpu_layers if n_gpu_layers > 0 else 0,
                    enable_thinking=False,
                    verbose=False,
                    use_mmap=True,
                    use_mlock=False,
                    n_batch=512,
                )
                logger.info("Model ready: qwen-gguf")
            except Exception as exc2:
                logger.warning(f"Failed with n_gpu_layers={n_gpu_layers}: {exc2}. Retrying on CPU (n_gpu_layers=0)...")
                model = Llama(
                    model_path=model_path,
                    n_ctx=2048,
                    n_threads=n_threads,
                    n_gpu_layers=0,
                    enable_thinking=False,
                    verbose=False,
                    use_mmap=True,
                    use_mlock=False,
                    n_batch=512,
                )
                logger.info("Model ready: qwen-gguf (CPU fallback)")
        _shared_llamas[key] = model
        _shared_llm = model
        return model


# Never surface raw model/exception internals in downstream output that may be
# rendered in the UI — a safe, static placeholder is used instead.
UNAVAILABLE_RESPONSE = "Model response unavailable for this analysis step."


class LlamaCppProvider(LLMProvider):
    """LLM provider using llama.cpp Python bindings for GGUF quantized models.

    Supports Qwen3 and DeepSeek-R1 quantized models with grammar-constrained
    structured output generation.
    """

    def __init__(
        self,
        model_name: str = "llama-cpp",
        model_path: str = "",
        n_ctx: int = 8192,
        n_threads: int = 8,
        n_gpu_layers: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model_name, **kwargs)
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self._model = None

        if model_path:
            self._load_model()

    def _load_model(self) -> None:
        """Load the GGUF model via the shared module-level cache."""
        try:
            gpu_layers = self.n_gpu_layers
            if gpu_layers > 0:
                if not _cuda_available():
                    # A CPU-only build ignores n_gpu_layers. Say so, or the
                    # operator will believe offload is active when it is not.
                    logger.warning(
                        "LLM_N_GPU_LAYERS is set but this llama-cpp-python build has no "
                        "CUDA backend, so the model will still run entirely on the CPU. "
                        "Rebuild with: pip install cmake && "
                        "CMAKE_ARGS='-DGGML_CUDA=on' pip install --force-reinstall "
                        "--no-cache-dir llama-cpp-python"
                    )
                    gpu_layers = 0
                else:
                    gpu_layers = _auto_gpu_layers(
                        self.model_path, self.n_gpu_layers, self.n_ctx
                    )

            self._model = _get_shared_llama(
                self.model_path, self.n_ctx, self.n_threads, gpu_layers
            )
            logger.info(
                f"Model ready: {self.model_name} "
                f"(gpu_layers={gpu_layers}, n_ctx={self.n_ctx})"
            )
        except ImportError:
            logger.warning("llama-cpp-python not installed. Using mock fallback.")
            self._model = None
        except Exception as exc:
            logger.error(f"Failed to load model: {exc}")
            self._model = None

    def _ensure_model(self) -> bool:
        """Ensure model is loaded; returns False if unavailable."""
        if self._model is None and self.model_path:
            self._load_model()
        return self._model is not None

    def _mock_fallback(self, op: str) -> None:
        """Record that a real generation is being replaced by mock output.

        This used to happen silently: when the GGUF could not be allocated the
        provider returned canned text and the run still reported success, so
        fabricated analysis was indistinguishable from a real one. The flag
        below is what analysis.py records in the case state.
        """
        global _MOCK_FALLBACK_ACTIVE
        _MOCK_FALLBACK_ACTIVE = True
        _warn_mock_once(op)

    def _cap_max_tokens(self, full_prompt: str, requested: int) -> int:
        """Clamp max_tokens so prompt + output fit in the context window.

        Requesting more than n_ctx - prompt_len makes llama.cpp truncate the
        generation mid-stream (cut JSON / cut analysis text).
        """
        try:
            n_ctx = self._model.n_ctx()
        except Exception:
                n_ctx=min(self.n_ctx, 8192)
        try:
            prompt_len = len(
                self._model.tokenize(full_prompt.encode("utf-8"), add_bos=True)
            )
        except Exception:
            prompt_len = n_ctx // 2
        return max(128, min(requested, n_ctx - prompt_len - 16))

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
        stop: list[str] | None = None,
    ) -> str:
        """Generate text using the loaded GGUF model.

        Falls back to mock responses if the model is unavailable.
        """
        if not self._ensure_model():
            from app.llm.mock_provider import MockProvider

            self._mock_fallback("generate")
            return MockProvider(self.model_name).generate(
                prompt, system_prompt, max_tokens, temperature, stop
            )

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        capped = self._cap_max_tokens(full_prompt, max_tokens)
        t0 = time.monotonic()
        try:
            result = self._model.create_completion(
                prompt=full_prompt,
                max_tokens=capped,
                temperature=temperature,
                stop=stop or [],
                echo=False,
                repeat_penalty=1.1,
            )
            text = result["choices"][0]["text"].strip()
            dt = time.monotonic() - t0
            logger.info(
                f"LLM generate done elapsed={dt:.1f}s max_tokens={capped} "
                f"chars={len(text)} speed~{max(1, len(text)//4)/max(dt,0.1):.1f} tok/s"
            )
            return text
        except Exception as exc:
            logger.error(f"LLM generation error: {exc}")
            return UNAVAILABLE_RESPONSE

    def generate_structured(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        system_prompt: str = "",
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Generate structured JSON using grammar-constrained generation.

        Falls back to regular generation + JSON parsing if grammar unavailable.
        """
        if not self._ensure_model():
            from app.llm.mock_provider import MockProvider

            self._mock_fallback("generate_structured")
            return MockProvider(self.model_name).generate_structured(
                prompt, output_schema, system_prompt, temperature, max_tokens
            )

        json_instruction = (
            f"Respond ONLY with valid JSON conforming to this schema:\n"
            f"{json.dumps(output_schema, indent=2)}\n\n"
            f"{prompt}"
        )

        # Generation budget. On a CPU backend every extra token costs real wall
        # clock (measured ~2.7-5 tok/s), so an oversized default turned one
        # agent into a 10+ minute call. Callers pass the smallest budget that
        # fits their schema; None keeps the previous 4096 default.
        budget = 4096 if max_tokens is None else max_tokens
        try:
            # Try grammar-constrained generation
            schema_str = json.dumps(output_schema)
            grammar_prompt = f"{system_prompt}\n\n{json_instruction}"
            result = self._model.create_completion(
                prompt=grammar_prompt,
                max_tokens=self._cap_max_tokens(grammar_prompt, budget),
                temperature=temperature,
                grammar=json.dumps(
                    {
                        "type": "object",
                        "properties": {
                            key: value
                            for key, value in self._simplify_schema(output_schema).items()
                        },
                    }
                ),
            )
            return json.loads(result["choices"][0]["text"])
        except Exception:
            # Fallback: regular generation then parse JSON
            response = self.generate(
                json_instruction,
                system_prompt,
                max_tokens=budget,
                temperature=temperature,
            )
            try:
                # Extract JSON block from response
                import re

                json_match = re.search(r"\{[\s\S]*\}", response)
                if json_match:
                    return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
            return {"raw_response": response, "parse_error": True}

    def stream_generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ):
        """Stream token-by-token generation."""
        if not self._ensure_model():
            from app.llm.mock_provider import MockProvider

            self._mock_fallback("stream_generate")
            yield from MockProvider(self.model_name).stream_generate(
                prompt, system_prompt, max_tokens, temperature
            )
            return

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        try:
            stream = self._model.create_completion(
                prompt=full_prompt,
                max_tokens=self._cap_max_tokens(full_prompt, max_tokens),
                temperature=temperature,
                stream=True,
            )
            for chunk in stream:
                text = chunk["choices"][0].get("text", "")
                if text:
                    yield text
        except Exception as exc:
            logger.error(f"Stream error: {exc}")
            yield UNAVAILABLE_RESPONSE

    @staticmethod
    def _simplify_schema(schema: dict[str, Any]) -> dict[str, Any]:
        """Simplify JSON schema for llama.cpp grammar compatibility."""
        simplified = {}
        if "properties" in schema:
            for key, value in schema["properties"].items():
                if value.get("type") == "string":
                    simplified[key] = {"type": "string"}
                elif value.get("type") == "number" or value.get("type") == "integer":
                    simplified[key] = {"type": "number"}
                elif value.get("type") == "boolean":
                    simplified[key] = {"type": "boolean"}
                elif value.get("type") == "array":
                    simplified[key] = {"type": "array", "items": {"type": "string"}}
                elif value.get("type") == "object":
                    simplified[key] = {"type": "object"}
                else:
                    simplified[key] = {"type": "string"}
        return simplified
