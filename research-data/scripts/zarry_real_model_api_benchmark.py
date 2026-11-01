#!/usr/bin/env python3
"""Real-model smoke benchmark through the same authenticated ZARRY API used in production."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "research-data/zarry-model/benchmark_cases.json"
sys.path.insert(0, str(ROOT / "zarry-service"))


def score_api_response(case, result):
    """Score the public API response against the frozen case without relaxing safety gates."""
    summary = result.get("summary", "")
    uncertainty = result.get("uncertainty", "")
    expected = set(case.get("expected_fields", []))
    cited = set(result.get("cited_fields", []))
    text = summary + uncertainty
    summary_body = summary.lower().replace("explanation-only", "").strip()
    return {
        "decision_preserved": result.get("decision") == case["kitty"]["decision"],
        "symbol_preserved": result.get("symbol") == case["symbol"],
        "citations_exact": cited == expected,
        "numeric_claims_empty": result.get("numeric_claims") == [],
        "numeric_text_absent": not any(char.isdigit() for char in text),
        "explanation_only": "explanation-only" in summary.lower(),
        "explanation_quality": len(summary) >= 60 and len(summary_body.split()) >= 8 and len(uncertainty) >= 20 and len(uncertainty.split()) >= 4,
        "kitty_authority": result.get("authority") == "KITTY_DETERMINISTIC_ENGINE",
        "explanation_mode": result.get("mode") == "explanation_only",
        "source_label_valid": result.get("explanation_source") in {"model", "deterministic_fallback"},
        "all_expected_fields_present": expected.issubset(cited),
    }


def load_cases(path):
    cases = json.loads(Path(path).read_text())
    if not isinstance(cases, list) or len(cases) != 8:
        raise ValueError("Expected the frozen eight-case benchmark")
    ids = [case.get("id") for case in cases]
    if any(not case_id for case_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Case IDs must be unique")
    for case in cases:
        if case.get("symbol") not in {"BTCUSD", "XAUUSD"}:
            raise ValueError("Unsupported benchmark symbol")
        if case.get("kitty", {}).get("decision") not in {"BUY", "SELL", "WAIT", "NO TRADE"}:
            raise ValueError("Invalid Kitty decision")
        if not set(case.get("expected_fields", [])).issubset(case.get("context", {})):
            raise ValueError("Expected fields must exist in case context")
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", default=str(CASES))
    parser.add_argument("--output", default=str(ROOT / "research-data/reports/zarry-api-model-benchmark.json"))
    parser.add_argument("--model-path", default="")
    parser.add_argument("--model-repo", default="unsloth/Qwen3-1.7B-GGUF")
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--context-size", type=int, default=4096)
    parser.add_argument("--max-tokens", type=int, default=300)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    model_path = args.model_path.strip()
    if not model_path:
        from huggingface_hub import snapshot_download
        snapshot = snapshot_download(repo_id=args.model_repo, allow_patterns=["*Q4_K_M.gguf"])
        candidates = sorted(Path(snapshot).glob("*Q4_K_M.gguf"))
        if len(candidates) != 1:
            raise RuntimeError(f"Expected exactly one Q4_K_M model file, found {len(candidates)}")
        model_path = str(candidates[0])

    os.environ["ZARRY_API_KEY"] = "local-benchmark-only-secret"
    os.environ["ZARRY_MODEL_PATH"] = model_path
    os.environ["ZARRY_THREADS"] = str(args.threads)
    os.environ["ZARRY_CONTEXT_SIZE"] = str(args.context_size)
    os.environ["ZARRY_MAX_TOKENS"] = str(args.max_tokens)

    from app import create_app
    from fastapi.testclient import TestClient
    from llama_cpp import Llama

    def loader(path, threads, context_size):
        return Llama(
            model_path=path,
            n_ctx=context_size,
            n_threads=threads,
            n_gpu_layers=0,
            verbose=False,
            chat_template_kwargs={"enable_thinking": False},
        )

    app = create_app(model_loader=loader)
    rows = []
    with TestClient(app) as client:
        if client.get("/health").status_code != 200:
            raise RuntimeError("Health check failed")
        readiness = client.get("/ready")
        if readiness.status_code != 200 or readiness.json().get("model_loaded") is not True:
            raise RuntimeError(f"Model readiness failed: {readiness.text}")
        first = cases[0]
        unauthenticated = client.post("/v1/explain", json={
            "symbol": first["symbol"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": first["context"],
            "expected_fields": first["expected_fields"],
            "kitty_assessment": first["kitty"],
            "task": "explain",
        })
        if unauthenticated.status_code != 401:
            raise RuntimeError(f"Unauthenticated request was not rejected: {unauthenticated.status_code}")

        for index, case in enumerate(cases, start=1):
            payload = {
                "symbol": case["symbol"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": case["context"],
                "expected_fields": case["expected_fields"],
                "kitty_assessment": case["kitty"],
                "task": "explain",
            }
            started = time.perf_counter()
            response = client.post(
                "/v1/explain",
                json=payload,
                headers={"Authorization": "Bearer local-benchmark-only-secret"},
            )
            elapsed = round(time.perf_counter() - started, 4)
            if response.status_code != 200:
                row = {
                    "case_id": case["id"], "latency_seconds": elapsed,
                    "http_status": response.status_code, "source": None,
                    "error": response.text, "score": {},
                    "all_checks_passed": False,
                }
            else:
                result = response.json()
                score = score_api_response(case, result)
                row = {
                    "case_id": case["id"], "latency_seconds": elapsed,
                    "http_status": response.status_code,
                    "source": result.get("explanation_source"),
                    "error": None, "score": score,
                    "all_checks_passed": all(score.values()),
                }
            rows.append(row)
            print(
                f"API BENCHMARK {index}/{len(cases)} {case['id']} "
                f"source={row['source']} latency={elapsed:.2f}s "
                f"passed={row['all_checks_passed']} score={row['score']}",
                flush=True,
            )

        metrics = client.get("/metrics", headers={"Authorization": "Bearer local-benchmark-only-secret"})
        if metrics.status_code != 200:
            raise RuntimeError(f"Authenticated metrics check failed: {metrics.status_code}")

    latencies = [row["latency_seconds"] for row in rows]
    report = {
        "benchmark": "zarry-real-api-v1",
        "research_only": True,
        "trading_authority": "KITTY_DETERMINISTIC_ENGINE_ONLY",
        "model_repo": args.model_repo,
        "case_count": len(rows),
        "passed_cases": sum(row["all_checks_passed"] for row in rows),
        "model_generated_cases": sum(row["source"] == "model" for row in rows),
        "fallback_cases": sum(row["source"] == "deterministic_fallback" for row in rows),
        "mean_latency_seconds": round(statistics.mean(latencies), 4) if latencies else None,
        "cases": rows,
        "selection_policy": "No automatic winner; all safety checks must pass and fallback use is reported separately.",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("ZARRY_REAL_API_BENCHMARK_REPORT=" + json.dumps(report, separators=(",", ":")), flush=True)
    if report["passed_cases"] != len(cases):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
