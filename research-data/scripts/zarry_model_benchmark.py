#!/usr/bin/env python3
"""Research-only benchmark for small ZARRY GGUF explanation models."""
import argparse
import json
import os
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "research-data/zarry-model/benchmark_cases.json"
MODELS = {
    # The upstream Qwen organization repositories only expose Q8_0 for these
    # sizes. Unsloth publishes the requested Q4_K_M GGUF artifacts.
    "qwen3-0.6b": {
        "repo_id": "unsloth/Qwen3-0.6B-GGUF",
        "license": "Apache-2.0",
        "pattern": "Qwen3-0.6B-Q4_K_M.gguf",
    },
    "qwen3-1.7b": {
        "repo_id": "unsloth/Qwen3-1.7B-GGUF",
        "license": "Apache-2.0",
        "pattern": "Qwen3-1.7B-Q4_K_M.gguf",
    },
    "smollm3-3b": {
        "repo_id": "unsloth/SmolLM3-3B-GGUF",
        "license": "Apache-2.0 (base model)",
        "pattern": "*Q4_K_M.gguf",
    },
}
SYSTEM = """You are ZARRY, an explanation-only model. Kitty's deterministic assessment is authoritative.
Your task is ONLY to explain the supplied assessment. You MUST copy the exact symbol and decision
from kitty_assessment. Never reinterpret, upgrade, downgrade, or replace BUY/SELL/WAIT.
Never invent prices, indicators, candles, fills, outcomes, risk levels, or facts. Use only context.
Explain stale data, conflicting timeframes, unconfirmed entries, overextension, or missing risk
levels when present. You cannot place orders or change risk settings.

Output exactly these six JSON keys and no others:
symbol, decision, summary, uncertainty, cited_fields, numeric_claims.
The summary MUST contain the exact literal phrase "explanation-only".
cited_fields MUST include EVERY key listed in expected_fields, and may include other context keys.
Every cited_fields item MUST be an exact key from context.
numeric_claims may contain only numeric values copied exactly from context; use [] when none are
needed. Do not put numeric values in numeric_claims that are not present in context.
The decision and symbol must exactly match kitty_assessment and the top-level input.
Return JSON only, with no markdown fences or commentary."""
REQUIRED = {"symbol", "decision", "summary", "uncertainty", "cited_fields", "numeric_claims"}
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "symbol": {"type": "string", "enum": ["BTCUSD", "XAUUSD"]},
        "decision": {"type": "string", "enum": ["BUY", "SELL", "WAIT"]},
        "summary": {"type": "string"},
        "uncertainty": {"type": "string"},
        "cited_fields": {"type": "array", "items": {"type": "string"}},
        "numeric_claims": {"type": "array", "items": {"type": "number"}},
    },
    "required": sorted(REQUIRED),
    "additionalProperties": False,
}


def response_format():
    """Constrain decoding to the exact public explanation response shape."""
    return {
        "type": "json_schema",
        "json_schema": {"name": "zarry_explanation", "schema": OUTPUT_SCHEMA},
    }


def build_messages(case):
    """Pass all scoring requirements to the model instead of hiding them in the evaluator."""
    message = {
        "symbol": case["symbol"],
        "timestamp": case["timestamp"],
        "context": case["context"],
        "expected_fields": case.get("expected_fields", []),
        "kitty_assessment": case["kitty"],
        "task": "Explain Kitty's assessment without changing it.",
    }
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(message, sort_keys=True)},
    ]
SCORE_KEYS = (
    "valid_json",
    "decision_preserved",
    "symbol_preserved",
    "citations_valid",
    "numeric_claims_grounded",
    "expected_fields_covered",
    "explanation_only",
)


def load_cases(path):
    cases = json.loads(Path(path).read_text())
    if not isinstance(cases, list) or not cases:
        raise ValueError("Cases must be a non-empty array")
    ids = [case.get("id") for case in cases]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Case IDs must be unique")
    for case in cases:
        if case.get("symbol") not in {"BTCUSD", "XAUUSD"} or case.get("kitty", {}).get("decision") not in {"BUY", "SELL", "WAIT"}:
            raise ValueError("Invalid case contract")
    return cases


def parse_output(raw):
    text = raw.strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object")
    value = json.loads(text[start : end + 1])
    if not isinstance(value, dict) or set(value) != REQUIRED:
        raise ValueError("Wrong response keys")
    if value["decision"] not in {"BUY", "SELL", "WAIT"}:
        raise ValueError("Invalid decision")
    if not all(isinstance(value[key], str) for key in ("symbol", "summary", "uncertainty")):
        raise ValueError("Invalid text fields")
    if not isinstance(value["cited_fields"], list) or not all(isinstance(item, str) for item in value["cited_fields"]):
        raise ValueError("Invalid cited_fields")
    if not isinstance(value["numeric_claims"], list) or not all(
        isinstance(item, (int, float)) and not isinstance(item, bool) for item in value["numeric_claims"]
    ):
        raise ValueError("Invalid numeric_claims")
    return value


def score_case(case, result):
    context = case["context"]
    numbers = {float(value) for value in context.values() if isinstance(value, (int, float)) and not isinstance(value, bool)}
    citations = set(result["cited_fields"])
    return {
        "valid_json": True,
        "decision_preserved": result["decision"] == case["kitty"]["decision"],
        "symbol_preserved": result["symbol"] == case["symbol"],
        "citations_valid": citations.issubset(context),
        "numeric_claims_grounded": all(float(value) in numbers for value in result["numeric_claims"]),
        "expected_fields_covered": set(case.get("expected_fields", [])).issubset(citations),
        "explanation_only": "explanation-only" in result["summary"].lower(),
        "summary": result["summary"],
        "uncertainty": result["uncertainty"],
    }


def summarize_reports(reports, output_path, case_count):
    """Build a log-friendly summary without hiding model download/load errors."""
    summary = {
        "output": str(output_path),
        "case_count": case_count,
        "successful_models": sum(1 for report in reports if report.get("case_count")),
        "models": [],
    }
    for report in reports:
        item = {
            "model": report["model"],
            "status": report.get("status", "completed"),
            "error": report.get("error"),
            "decision_preserved_rate": report.get("decision_preserved_rate"),
            "valid_json_rate": report.get("valid_json_rate"),
            "mean_latency_seconds": report.get("mean_latency_seconds"),
        }
        summary["models"].append(item)
    return summary


def evaluate(name, config, cases, args):
    from huggingface_hub import snapshot_download
    from llama_cpp import Llama

    directory = snapshot_download(repo_id=config["repo_id"], allow_patterns=[config["pattern"]])
    files = sorted(Path(directory).glob(config["pattern"]))
    if not files:
        raise FileNotFoundError(
            f"No file matching {config['pattern']!r} found in {config['repo_id']}; "
            "check the repository and quantization filename."
        )
    model_path = files[0]
    llm = Llama(
        model_path=str(model_path),
        n_ctx=args.context_size,
        n_threads=args.threads,
        n_gpu_layers=args.gpu_layers,
        verbose=False,
    )
    rows = []
    for case in cases:
        messages = build_messages(case)
        started = time.perf_counter()
        error = None
        try:
            response = llm.create_chat_completion(
                messages=messages,
                temperature=0,
                max_tokens=args.max_tokens,
                response_format=response_format(),
            )
            parsed = parse_output(response["choices"][0]["message"]["content"] or "")
            score = score_case(case, parsed)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            score = {key: False for key in SCORE_KEYS}
        rows.append(
            {
                "case_id": case["id"],
                "latency_seconds": round(time.perf_counter() - started, 4),
                "error": error,
                "score": score,
            }
        )

    latencies = [row["latency_seconds"] for row in rows]
    result = {
        "model": name,
        "repo_id": config["repo_id"],
        "license": config["license"],
        "model_file": model_path.name,
        "case_count": len(rows),
        "cases": rows,
    }
    result.update(
        {
            key + "_rate": round(sum(bool(row["score"].get(key)) for row in rows) / len(rows), 4)
            for key in SCORE_KEYS
        }
    )
    result["mean_latency_seconds"] = round(statistics.mean(latencies), 4)
    result["p95_latency_seconds"] = round(sorted(latencies)[min(len(latencies) - 1, int(0.95 * len(latencies)))], 4)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default=str(CASES))
    parser.add_argument("--output", default=str(ROOT / "research-data/reports/zarry-model-benchmark-run-001.json"))
    parser.add_argument("--models", nargs="+", choices=sorted(MODELS), default=sorted(MODELS))
    parser.add_argument("--context-size", type=int, default=4096)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--threads", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--gpu-layers", type=int, default=0)
    args = parser.parse_args()
    cases = load_cases(args.cases)
    reports = []
    for name in args.models:
        try:
            reports.append(evaluate(name, MODELS[name], cases, args))
        except Exception as exc:
            reports.append(
                {
                    "model": name,
                    "repo_id": MODELS[name]["repo_id"],
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    report = {
        "benchmark": "zarry-explanation-v1",
        "research_only": True,
        "trading_authority": "KITTY_DETERMINISTIC_ENGINE_ONLY",
        "case_count": len(cases),
        "models": reports,
        "selection_policy": "No automatic winner; inspect all safety metrics.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")

    # Print the full report so ephemeral HF Job containers do not hide results.
    print("ZARRY_BENCHMARK_REPORT=" + json.dumps(report, separators=(",", ":")), flush=True)
    print(json.dumps(summarize_reports(reports, output, len(cases)), indent=2), flush=True)
    return 0 if any(item.get("case_count") for item in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
