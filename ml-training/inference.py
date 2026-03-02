#!/usr/bin/env python3
"""
Test the trained summarizer (ONNX + SentencePiece) from Python.
Usage:
  python inference.py "Input text to summarize..."
  python inference.py   # read from stdin
  python -c "from inference import load_summarizer, summarize; s=load_summarizer(); print(summarize(s, 'Your text'))"
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def load_config():
    cfg = {
        "data": {"max_input_len": 512, "max_output_len": 128},
        "output": {"dir": "output", "onnx_name": "summarizer.onnx", "tokenizer_name": "tokenizer.model"},
    }
    try:
        import yaml
        config_path = SCRIPT_DIR / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                user = yaml.safe_load(f) or {}
            for k, v in user.items():
                if k in cfg and isinstance(v, dict) and isinstance(cfg[k], dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
    except ImportError:
        pass
    return cfg


def load_summarizer(model_dir: str | Path | None = None):
    import numpy as np
    import onnxruntime as ort
    import sentencepiece as spm

    cfg = load_config()
    out_dir = SCRIPT_DIR / (model_dir or cfg["output"]["dir"])
    onnx_path = out_dir / cfg["output"].get("onnx_name", "summarizer.onnx")
    tokenizer_path = out_dir / cfg["output"].get("tokenizer_name", "tokenizer.model")
    if not onnx_path.exists() or not tokenizer_path.exists():
        raise FileNotFoundError(
            f"Model not found. Run train.py first. Expected {onnx_path} and {tokenizer_path}"
        )
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    sp = spm.SentencePieceProcessor()
    sp.load(str(tokenizer_path))
    max_in = cfg["data"].get("max_input_len", 512)
    max_out = cfg["data"].get("max_output_len", 128)
    return {
        "session": session,
        "tokenizer": sp,
        "max_input_len": max_in,
        "max_output_len": max_out,
    }


def summarize(state: dict, text: str, max_output_len: int | None = None) -> str:
    import numpy as np

    session = state["session"]
    sp = state["tokenizer"]
    max_in = state["max_input_len"]
    max_out = max_output_len or state["max_output_len"]
    pad_id = sp.pad_id()
    eos_id = sp.eos_id()
    bos_id = sp.bos_id()

    ids = sp.encode(text, out_type=int)
    ids = ids[:max_in] + [eos_id]
    ids = ids + [pad_id] * (max_in - len(ids))
    input_ids = np.array([ids], dtype=np.int64)

    decoder_ids = [bos_id]
    for _ in range(max_out - 1):
        decoder_input = np.array([decoder_ids], dtype=np.int64)
        logits, = session.run(
            None,
            {"input_ids": input_ids, "decoder_input_ids": decoder_input},
        )
        next_id = int(logits[0, -1, :].argmax())
        if next_id == eos_id:
            break
        decoder_ids.append(next_id)

    return sp.decode(decoder_ids[1:])


def main():
    cfg = load_config()
    try:
        state = load_summarizer()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    max_out = cfg["data"].get("max_output_len", 128)
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read().strip()
    if not text:
        print("Usage: python inference.py \"Text to summarize...\"", file=sys.stderr)
        print("   or: echo \"Text\" | python inference.py", file=sys.stderr)
        sys.exit(0)
    summary = summarize(state, text, max_output_len=max_out)
    print(summary)


if __name__ == "__main__":
    main()
