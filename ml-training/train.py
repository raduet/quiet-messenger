#!/usr/bin/env python3
"""
Train Quiet summarizer: load data from datasets/, train small seq2seq,
export ONNX and SentencePiece tokenizer to output/ for use in the app.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(SCRIPT_DIR)

try:
    import sentencepiece as spm
except ImportError:
    print("Install: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


def load_config():
    cfg = {
        "data": {
            "train_csv": "datasets/train.csv",
            "train_json": None,
            "max_input_len": 512,
            "max_output_len": 128,
        },
        "tokenizer": {"vocab_size": 8000, "model_path": "output/tokenizer.model"},
        "train": {
            "batch_size": 8,
            "epochs": 10,
            "lr": 1e-4,
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "hidden_size": 256,
            "num_layers": 2,
            "dropout": 0.1,
        },
        "output": {
            "dir": "output",
            "onnx_name": "summarizer.onnx",
            "tokenizer_name": "tokenizer.model",
            "checkpoint_name": "checkpoint.pt",
        },
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


def load_dataset(cfg):
    data = []
    train_csv = cfg["data"].get("train_csv") or "datasets/train.csv"
    train_json = cfg["data"].get("train_json")
    csv_path = SCRIPT_DIR / train_csv
    if train_json:
        json_path = SCRIPT_DIR / train_json
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
    if not data and csv_path.exists():
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                inp = row.get("input_text", "").strip()
                out = row.get("summary_text", "").strip()
                if inp and out:
                    data.append({"input_text": inp, "summary_text": out})
    if not data:
        raise SystemExit(
            f"No data found. Put train.csv (columns: input_text, summary_text) in datasets/ or set train_json in config.yaml."
        )
    return data


def train_tokenizer(data, cfg):
    out_dir = SCRIPT_DIR / cfg["output"]["dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = Path(cfg["tokenizer"]["model_path"])
    if model_path.is_absolute():
        sp_model_path = model_path
    else:
        sp_model_path = SCRIPT_DIR / model_path
    sp_model_path.parent.mkdir(parents=True, exist_ok=True)
    vocab_size = cfg["tokenizer"].get("vocab_size", 8000)
    corpus_path = out_dir / "_corpus.txt"
    with open(corpus_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(item["input_text"].replace("\n", " ") + "\n")
            f.write(item["summary_text"].replace("\n", " ") + "\n")
    spm.SentencePieceTrainer.train(
        input=str(corpus_path),
        model_prefix=str(sp_model_path.with_suffix("")),
        vocab_size=vocab_size,
        model_type="unigram",
        pad_id=0,
        unk_id=1,
        bos_id=2,
        eos_id=3,
    )
    corpus_path.unlink(missing_ok=True)
    return str(sp_model_path.with_suffix(".model"))


class Seq2Seq(nn.Module):
    def __init__(self, vocab_size, hidden_size, num_layers, dropout, pad_id, eos_id):
        super().__init__()
        self.pad_id = pad_id
        self.eos_id = eos_id
        self.hidden_size = hidden_size
        self.embed = nn.Embedding(vocab_size, hidden_size, padding_idx=pad_id)
        self.encoder = nn.LSTM(
            hidden_size, hidden_size, num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0
        )
        self.decoder = nn.LSTM(
            hidden_size, hidden_size, num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0
        )
        self.proj = nn.Linear(hidden_size, vocab_size)

    def forward(self, input_ids, decoder_input_ids=None, max_decode_len=None):
        enc_emb = self.embed(input_ids)
        _, (h, c) = self.encoder(enc_emb)
        if decoder_input_ids is not None:
            dec_emb = self.embed(decoder_input_ids)
            out, _ = self.decoder(dec_emb, (h, c))
            logits = self.proj(out)
            return logits
        batch = input_ids.size(0)
        device = input_ids.device
        max_len = max_decode_len or 128
        logits_list = []
        dec_h, dec_c = h, c
        prev = self.embed(torch.full((batch, 1), self.eos_id, dtype=torch.long, device=device))
        for _ in range(max_len - 1):
            out, (dec_h, dec_c) = self.decoder(prev, (dec_h, dec_c))
            logits_list.append(self.proj(out))
            next_id = logits_list[-1].argmax(dim=-1)
            prev = self.embed(next_id)
        logits = torch.cat(logits_list, dim=1)
        return logits


def run_training(data, tokenizer_path, cfg):
    sp = spm.SentencePieceProcessor()
    sp.load(tokenizer_path)
    pad_id = sp.pad_id()
    eos_id = sp.eos_id()
    bos_id = sp.bos_id()
    vocab_size = sp.get_piece_size()
    max_in = cfg["data"].get("max_input_len", 512)
    max_out = cfg["data"].get("max_output_len", 128)
    device = cfg["train"].get("device", "cpu")
    if device == "cuda" and not torch.cuda.is_available():
        device = "cpu"
    device = torch.device(device)
    batch_size = cfg["train"].get("batch_size", 8)
    epochs = cfg["train"].get("epochs", 10)
    lr = cfg["train"].get("lr", 1e-4)
    hidden_size = cfg["train"].get("hidden_size", 256)
    num_layers = cfg["train"].get("num_layers", 2)
    dropout = cfg["train"].get("dropout", 0.1)

    def encode(texts, max_len, add_eos=True, add_bos=False):
        ids_list = []
        for t in texts:
            ids = sp.encode(t, out_type=int)
            if add_bos:
                ids = [bos_id] + ids
            if add_eos:
                ids = ids + [eos_id]
            ids = ids[:max_len]
            ids = ids + [pad_id] * (max_len - len(ids))
            ids_list.append(ids)
        return torch.tensor(ids_list, dtype=torch.long, device=device)

    model = Seq2Seq(vocab_size, hidden_size, num_layers, dropout, pad_id, eos_id).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    ce = nn.CrossEntropyLoss(ignore_index=pad_id)

    for epoch in range(epochs):
        model.train()
        np.random.shuffle(data)
        total_loss = 0.0
        n_batches = 0
        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]
            in_texts = [x["input_text"] for x in batch]
            out_texts = [x["summary_text"] for x in batch]
            input_ids = encode(in_texts, max_in)
            dec_in = encode(out_texts, max_out, add_eos=False, add_bos=True)
            dec_out_ids = encode(out_texts, max_out)
            logits = model(input_ids, decoder_input_ids=dec_in)
            loss = ce(logits.view(-1, vocab_size), dec_out_ids.view(-1))
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            total_loss += loss.item()
            n_batches += 1
        print(f"Epoch {epoch + 1}/{epochs} loss={total_loss / max(n_batches, 1):.4f}")

    out_dir = SCRIPT_DIR / cfg["output"]["dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / cfg["output"].get("checkpoint_name", "checkpoint.pt")
    torch.save({"model": model.state_dict(), "vocab_size": vocab_size, "pad_id": pad_id, "eos_id": eos_id}, ckpt_path)
    return model, sp, vocab_size, pad_id, eos_id, max_in, max_out


def export_onnx(model, sp, vocab_size, pad_id, eos_id, max_in, max_out, cfg):
    out_dir = SCRIPT_DIR / cfg["output"]["dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = out_dir / cfg["output"].get("onnx_name", "summarizer.onnx")
    device = next(model.parameters()).device
    model.eval()
    dummy_input = torch.zeros(1, max_in, dtype=torch.long, device=device)
    dummy_decoder = torch.full((1, max_out), pad_id, dtype=torch.long, device=device)
    dummy_decoder[0, 0] = sp.bos_id()
    with torch.no_grad():
        logits = model(dummy_input, decoder_input_ids=dummy_decoder)
    torch.onnx.export(
        model,
        (dummy_input, dummy_decoder),
        str(onnx_path),
        input_names=["input_ids", "decoder_input_ids"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "in_len"},
            "decoder_input_ids": {0: "batch", 1: "dec_len"},
            "logits": {0: "batch", 1: "dec_len"},
        },
        opset_version=14,
    )
    print(f"Exported {onnx_path}")
    return onnx_path


def main():
    cfg = load_config()
    data = load_dataset(cfg)
    print(f"Loaded {len(data)} samples")
    tokenizer_path = train_tokenizer(data, cfg)
    print(f"Tokenizer: {tokenizer_path}")
    model, sp, vocab_size, pad_id, eos_id, max_in, max_out = run_training(data, tokenizer_path, cfg)
    export_onnx(model, sp, vocab_size, pad_id, eos_id, max_in, max_out, cfg)
    out_dir = SCRIPT_DIR / cfg["output"]["dir"]
    tokenizer_out = out_dir / cfg["output"].get("tokenizer_name", "tokenizer.model")
    if Path(tokenizer_path).resolve() != tokenizer_out.resolve():
        import shutil
        shutil.copy2(tokenizer_path, tokenizer_out)
    print(f"Done. Outputs in {out_dir}: summarizer.onnx, tokenizer.model")


if __name__ == "__main__":
    main()
