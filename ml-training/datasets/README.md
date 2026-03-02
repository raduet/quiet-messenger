# Datasets for Quiet summarizer

Put your training data here.

## Format

**CSV** (recommended): `datasets/train.csv` with columns:

- `input_text` — long text (e.g. concatenated messages)
- `summary_text` — short summary (2–3 sentences)

Example:

```csv
input_text,summary_text
"Message one. Message two. Message three.","Summary in one or two sentences."
```

**JSON** (alternative): `datasets/train.json` — list of objects:

```json
[
  {"input_text": "...", "summary_text": "..."},
  ...
]
```

**Parquet**: `datasets/train.parquet` with columns `input_text` and `summary_text`. Set in `config.yaml`:

```yaml
data:
  train_parquet: "datasets/train.parquet"
```

Requires `pip install pyarrow`.

**DialogSum (Hugging Face style)**: folder with `data/train-*.parquet` and columns `dialogue` / `summary` (e.g. `datasets/dialogsum-ru`). Set in `config.yaml`:

```yaml
data:
  train_dialogsum_dir: "datasets/dialogsum-ru"
```

The loader reads all `data/train-*.parquet` files and maps `dialogue` → input, `summary` → summary. Requires `pip install pyarrow`.

Encoding: UTF-8 (CSV/JSON).

## Sample

A minimal `sample.csv` is provided. Replace or add your own `train.csv` / `train.json` / `train.parquet`, or use `train_dialogsum_dir: "datasets/dialogsum-ru"` for the DialogSum RU corpus.
