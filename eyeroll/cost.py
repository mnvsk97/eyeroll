"""Cost estimation for eyeroll analysis runs."""

# Pricing per million tokens (USD) — input / output
MODEL_PRICING = {
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash": (0.10, 0.40),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "llama-3.3-70b-versatile": (0.00, 0.00),
    "grok-2-vision-1212": (2.00, 10.00),
}

_DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash", "openai": "gpt-4o", "groq": "llama-3.3-70b-versatile",
    "grok": "grok-2-vision-1212", "openrouter": "openai/gpt-4o", "cerebras": "llama3.1-70b",
    "ollama": "qwen3-vl", "eyeroll-api": "gemini-2.5-flash",
}


def estimate_cost(backend_label, model=None, num_frames=0, has_audio=False,
                  audio_duration_s=0.0, direct_video=False,
                  actual_input_tokens=None, actual_output_tokens=None):
    """Estimate cost. Returns dict with input_tokens, output_tokens, cost_usd, model, is_estimate."""
    if backend_label == "ollama":
        return {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
                "model": model or "local", "is_estimate": False}

    model = model or _DEFAULT_MODELS.get(backend_label, "unknown")
    in_price, out_price = MODEL_PRICING.get(model, (0.0, 0.0))

    in_tok = actual_input_tokens if actual_input_tokens is not None else (
        (5000 + 3000) if direct_video else (num_frames * 1500 + 3000))
    out_tok = actual_output_tokens if actual_output_tokens is not None else (
        800 * max(1, num_frames) + 1500)

    cost = (in_tok * in_price + out_tok * out_price) / 1_000_000
    if has_audio and backend_label == "openai":
        cost += (audio_duration_s / 60) * 0.006

    return {"input_tokens": in_tok, "output_tokens": out_tok, "cost_usd": cost,
            "model": model, "is_estimate": actual_input_tokens is None}


def format_cost(info):
    """Format cost info for stderr."""
    if info["cost_usd"] == 0:
        return f"Cost: $0.00 ({info['model']}, local)"
    e = "~" if info["is_estimate"] else ""
    return f"Cost: {e}${info['cost_usd']:.4f} ({info['model']}, {e}{info['input_tokens']} in / {e}{info['output_tokens']} out)"
