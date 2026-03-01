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

Encoding: UTF-8.

## Sample

A minimal `sample.csv` is provided. Replace or add your own `train.csv` / `train.json` for real training.
