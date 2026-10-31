# ZARRY model benchmark v1

Research-only comparison of open-weight GGUF models that explain an already-computed Kitty assessment. It does not train weights, fetch live market data, create signals, or execute orders.

| Candidate | Hugging Face repository | Base license |
|---|---|---|
| Qwen3 0.6B | https://huggingface.co/Qwen/Qwen3-0.6B-GGUF | Apache-2.0 |
| Qwen3 1.7B | https://huggingface.co/Qwen/Qwen3-1.7B-GGUF | Apache-2.0 |
| SmolLM3 3B | https://huggingface.co/unsloth/SmolLM3-3B-GGUF | Apache-2.0 (base model) |

The runner downloads a Q4_K_M GGUF file at runtime. Recheck model repository contents and license metadata before redistributing weights.

The frozen eight-case synthetic suite covers BTCUSD/XAUUSD, BUY/SELL/WAIT, timeframe conflicts, stale data, overextension and missing risk context. It is a contract test, not a historical profitability dataset.

Install Python 3.12, llama-cpp-python and huggingface_hub, then run:
`python research-data/scripts/zarry_model_benchmark.py --models qwen3-0.6b qwen3-1.7b smollm3-3b --threads 4`

CPU-only is default. Actual inference is manual-only in GitHub Actions because model downloads and inference can consume substantial runner time. PR checks run only the lightweight contract tests.

Metrics include valid JSON, decision/symbol preservation, citation validity, numeric grounding, expected-field coverage, explanation-only wording and latency. No model is automatically selected. Kitty remains authoritative; no Railway, Vercel, broker, production checkpoint or trading permission is changed.
