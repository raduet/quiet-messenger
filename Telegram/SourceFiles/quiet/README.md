# Quiet — ML and digest

## Structure

- **digest/** — Data provider and types for the digest pipeline (no ML).
  - `digest_types.h` — `RawMessage`, `ChatMeta`, `Branch`, `Cluster`, `TreeSnapshot`.
  - `data_provider.h/cpp` — Collect messages and chat meta from session (stub; implement with `session().data()`, `history()`, `message()`).

- **ml/** — ML pipeline (tokenizer, summarizer, placeholders).
  - `tokenizer.h/cpp` — SentencePiece wrapper: load `.model`, encode/decode text ↔ token ids.
  - `summarizer.h/cpp` — ONNX summarizer: load `.onnx`, `summarize(messages)` → 2–3 sentences (stub).
  - `embedding.h`, `clustering.h` — Placeholders for future embedding and K-means–style clustering.

- **quiet_controller**, **quiet_mode_layer_widget**, **quiet_cover_button** — UI and entry points.

## Optional dependencies (Quiet ML)

Built only if sources are present under `Telegram/ThirdParty/`:

1. **ONNX Runtime** (for summarizer)
   - **Option A:** Do nothing — CMake will fetch tag v1.18.1 and build from source (recommended).
   - **Option B:** Use a local clone (e.g. for a specific version). If you had a clone that fails to configure (e.g. `onnx_proto` / `re2::re2` errors), remove or rename `Telegram/ThirdParty/onnxruntime` so Option A is used.
   ```bat
   git clone --depth 1 --branch v1.18.1 https://github.com/microsoft/onnxruntime.git Telegram/ThirdParty/onnxruntime
   ```
   Requires CMake 3.28+ and Python (for ONNX build).

2. **SentencePiece** (for tokenizer)
   ```bat
   git clone --depth 1 https://github.com/google/sentencepiece.git Telegram/ThirdParty/sentencepiece
   ```
   The repo should contain `VERSION.txt` in the root (standard clone has it).

If either is missing, the corresponding part of the ML pipeline is disabled; the app still builds.
