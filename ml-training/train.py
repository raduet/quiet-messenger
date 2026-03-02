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

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **kwargs):
        return it


def load_config():
    cfg = {
        "data": {
            "train_csv": "datasets/train.csv",
            "train_json": None,
            "train_parquet": None,
            "train_dialogsum_dir": None,
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
            "validation_split": 0.1,
            "save_every_epoch": True,
            "early_stopping_patience": 0,
        },
        "output": {
            "dir": "output",
            "onnx_name": "summarizer.onnx",
            "tokenizer_name": "tokenizer.model",
            "checkpoint_name": "checkpoint.pt",
            "checkpoint_best_name": "checkpoint_best.pt",
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


def _load_parquet(path: Path, input_col: str = "input_text", summary_col: str = "summary_text"):
    import pyarrow.parquet as pq
    table = pq.read_table(path)
    if input_col not in table.column_names or summary_col not in table.column_names:
        raise SystemExit(
            f"Parquet must have columns '{input_col}' and '{summary_col}', got {table.column_names}"
        )
    inp_col = table.column(input_col)
    out_col = table.column(summary_col)
    data = []
    for i in range(table.num_rows):
        inp = (inp_col[i].as_py() or "").strip() if inp_col[i].is_valid else ""
        out = (out_col[i].as_py() or "").strip() if out_col[i].is_valid else ""
        if inp and out:
            data.append({"input_text": str(inp), "summary_text": str(out)})
    return data


def _load_dialogsum_dir(dir_path: Path):
    data_dir = dir_path / "data"
    if not data_dir.is_dir():
        raise SystemExit(f"dialogsum dir must contain data/: {dir_path}")
    parquet_files = sorted(data_dir.glob("train-*.parquet"))
    if not parquet_files:
        raise SystemExit(f"No data/train-*.parquet found in {dir_path}")
    try:
        data = []
        for pq_path in parquet_files:
            data.extend(_load_parquet(pq_path, input_col="dialogue", summary_col="summary"))
        return data
    except ImportError:
        raise SystemExit("Parquet support requires pyarrow. Install: pip install pyarrow")


def load_dataset(cfg):
    data = []
    train_dialogsum_dir = cfg["data"].get("train_dialogsum_dir")
    train_parquet = cfg["data"].get("train_parquet")
    train_json = cfg["data"].get("train_json")
    train_csv = cfg["data"].get("train_csv") or "datasets/train.csv"
    if train_dialogsum_dir:
        ds_path = SCRIPT_DIR / train_dialogsum_dir
        if ds_path.is_dir():
            data = _load_dialogsum_dir(ds_path)
    if not data and train_parquet:
        pq_path = SCRIPT_DIR / train_parquet
        if pq_path.exists():
            try:
                data = _load_parquet(pq_path)
            except ImportError:
                raise SystemExit(
                    "Parquet support requires pyarrow. Install: pip install pyarrow"
                )
    if not data and train_json:
        json_path = SCRIPT_DIR / train_json
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
    if not data:
        csv_path = SCRIPT_DIR / train_csv
        if csv_path.exists():
            with open(csv_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    inp = row.get("input_text", "").strip()
                    out = row.get("summary_text", "").strip()
                    if inp and out:
                        data.append({"input_text": inp, "summary_text": out})
    if not data:
        raise SystemExit(
            "No data found. Put train.csv (columns: input_text, summary_text) in datasets/ "
            "or set train_json / train_parquet / train_dialogsum_dir in config.yaml."
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

    validation_split = cfg["train"].get("validation_split", 0.0)
    save_every_epoch = cfg["train"].get("save_every_epoch", True)
    early_stopping_patience = cfg["train"].get("early_stopping_patience", 0)

    if validation_split > 0 and validation_split < 1:
        n_val = max(1, int(len(data) * validation_split))
        np.random.shuffle(data)
        val_data = data[:n_val]
        train_data = data[n_val:]
    else:
        train_data = data
        val_data = []

    out_dir = SCRIPT_DIR / cfg["output"]["dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / cfg["output"].get("checkpoint_name", "checkpoint.pt")
    ckpt_best_path = out_dir / cfg["output"].get("checkpoint_best_name", "checkpoint_best.pt")

    model = Seq2Seq(vocab_size, hidden_size, num_layers, dropout, pad_id, eos_id).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    ce = nn.CrossEntropyLoss(ignore_index=pad_id)

    best_val_loss = float("inf")
    best_state = None
    epochs_without_improvement = 0
    n_batches_per_epoch = (len(train_data) + batch_size - 1) // batch_size

    def save_ckpt(path, state_dict):
        torch.save({
            "model": state_dict,
            "vocab_size": vocab_size,
            "pad_id": pad_id,
            "eos_id": eos_id,
        }, path)

    for epoch in range(epochs):
        model.train()
        np.random.shuffle(train_data)
        total_loss = 0.0
        n_batches = 0
        pbar = tqdm(
            range(0, len(train_data), batch_size),
            total=n_batches_per_epoch,
            desc=f"Epoch {epoch + 1}/{epochs}",
            unit="batch",
        )
        for i in pbar:
            batch = train_data[i : i + batch_size]
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
            pbar.set_postfix(loss=f"{loss.item():.4f}", avg=f"{total_loss / n_batches:.4f}")
        train_loss = total_loss / max(n_batches, 1)

        val_loss = None
        if val_data:
            model.eval()
            total_val_loss = 0.0
            n_val_batches = 0
            with torch.no_grad():
                for i in range(0, len(val_data), batch_size):
                    batch = val_data[i : i + batch_size]
                    in_texts = [x["input_text"] for x in batch]
                    out_texts = [x["summary_text"] for x in batch]
                    input_ids = encode(in_texts, max_in)
                    dec_in = encode(out_texts, max_out, add_eos=False, add_bos=True)
                    dec_out_ids = encode(out_texts, max_out)
                    logits = model(input_ids, decoder_input_ids=dec_in)
                    loss = ce(logits.view(-1, vocab_size), dec_out_ids.view(-1))
                    total_val_loss += loss.item()
                    n_val_batches += 1
            val_loss = total_val_loss / max(n_val_batches, 1)
            model.train()
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                save_ckpt(ckpt_best_path, model.state_dict())
                epochs_without_improvement = 0
            else:
                epochs_without_improvement += 1

        if save_every_epoch:
            save_ckpt(ckpt_path, model.state_dict())

        log_msg = f"Epoch {epoch + 1}/{epochs} train_loss={train_loss:.4f}"
        if val_loss is not None:
            log_msg += f" val_loss={val_loss:.4f}"
        print(log_msg)

        if early_stopping_patience > 0 and val_data and epochs_without_improvement >= early_stopping_patience:
            print(f"Early stopping after {epoch + 1} epochs (no val improvement for {early_stopping_patience} epochs)")
            break

    if best_state is not None:
        model.load_state_dict(best_state, strict=True)
        save_ckpt(ckpt_path, model.state_dict())

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
        dynamo=False,
    )
    print(f"Exported {onnx_path}")
    return onnx_path


def export_from_checkpoint(cfg):
    out_dir = SCRIPT_DIR / cfg["output"]["dir"]
    ckpt_path = out_dir / cfg["output"].get("checkpoint_name", "checkpoint.pt")
    tokenizer_path = out_dir / cfg["output"].get("tokenizer_name", "tokenizer.model")
    if not ckpt_path.exists() or not tokenizer_path.exists():
        raise SystemExit(f"Missing {ckpt_path} or {tokenizer_path}. Train first.")
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    vocab_size = ckpt["vocab_size"]
    pad_id = ckpt["pad_id"]
    eos_id = ckpt["eos_id"]
    hidden_size = cfg["train"].get("hidden_size", 256)
    num_layers = cfg["train"].get("num_layers", 2)
    dropout = cfg["train"].get("dropout", 0.1)
    max_in = cfg["data"].get("max_input_len", 512)
    max_out = cfg["data"].get("max_output_len", 128)
    model = Seq2Seq(vocab_size, hidden_size, num_layers, dropout, pad_id, eos_id)
    model.load_state_dict(ckpt["model"])
    model.eval()
    sp = spm.SentencePieceProcessor()
    sp.load(str(tokenizer_path))
    export_onnx(model, sp, vocab_size, pad_id, eos_id, max_in, max_out, cfg)
    print(f"Done. Exported to {out_dir}")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--export-only":
        cfg = load_config()
        export_from_checkpoint(cfg)
        return
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
