# Quiet ML training

Training pipeline for the Quiet summarizer model. Produces an ONNX model and a SentencePiece tokenizer that the Telegram app loads for digest summaries.

## Layout

- **`datasets/`** — Put your training data here (CSV or JSON). See `datasets/README.md`.
- **`output/`** — After training: `summarizer.onnx`, `tokenizer.model`, and optional checkpoints.
- **`train.py`** — Main script: train model, export ONNX, save tokenizer.
- **`config.yaml`** — Optional config (paths, hyperparameters). Defaults work if you put data in `datasets/`.

## Quick start

1. Create a venv and install deps:

   ```bash
   cd ml-training
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate  # Linux/macOS
   pip install -r requirements.txt
   ```

2. Add data: place `train.csv` (or `train.json`) in `datasets/` with columns `input_text` and `summary_text`. See `datasets/sample.csv`.

3. Run training:

   ```bash
   python train.py
   ```

4. Outputs appear in `output/`: `summarizer.onnx`, `tokenizer.model`. Copy them into the app resources or the path your C++ summarizer uses.

## Config

Optional `config.yaml` in this directory:

```yaml
data:
  train_csv: "datasets/train.csv"   # or train_json: "datasets/train.json"
  max_input_len: 512
  max_output_len: 128

tokenizer:
  vocab_size: 8000
  model_path: "output/tokenizer.model"

train:
  batch_size: 8
  epochs: 10
  lr: 1e-4
  device: "cuda"   # or "cpu"

output:
  dir: "output"
  onnx_name: "summarizer.onnx"
  tokenizer_name: "tokenizer.model"
```

## ONNX contract (for C++ summarizer)

- **Inputs:**  
  - `input_ids`: shape `[batch, in_len]`, int64 (encoder input, token IDs).  
  - `decoder_input_ids`: shape `[batch, dec_len]`, int64 (decoder input: start with `[BOS]`, then append predicted ids each step).
- **Output:** `logits`, shape `[batch, dec_len, vocab_size]`, float. The app runs the decoder step-by-step: feed current `decoder_input_ids`, take `argmax` of the last position logits, append to decoder input, repeat until EOS or max length, then decode IDs to text with the tokenizer.

Use the same `tokenizer.model` in the app as produced here. BOS/EOS/PAD ids are from SentencePiece (typically 2, 3, 0).
