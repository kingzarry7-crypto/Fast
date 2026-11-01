"""Real-model smoke for the isolated ZARRY explanation API.

Usage:
  python tests/zarry_real_model_api_smoke.py --cases /path/to/benchmark_cases.json \
      --service-dir /path/to/zarry-service
"""
import argparse
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

from huggingface_hub import snapshot_download
from fastapi.testclient import TestClient
from llama_cpp import Llama


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--service-dir", required=True)
    parser.add_argument("--model-repo", default="unsloth/Qwen3-1.7B-GGUF")
    parser.add_argument("--model-pattern", default="Qwen3-1.7B-Q4_K_M.gguf")
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text())
    snapshot = snapshot_download(repo_id=args.model_repo, allow_patterns=[args.model_pattern])
    model_path = next(Path(snapshot).glob(args.model_pattern), None)
    if model_path is None:
        raise FileNotFoundError(f"No model file matched {args.model_pattern}")

    os.environ.setdefault("ZARRY_API_KEY", "local-smoke-only-secret")
    os.environ["ZARRY_MODEL_PATH"] = str(model_path)
    os.environ.setdefault("ZARRY_THREADS", "2")
    os.environ.setdefault("ZARRY_CONTEXT_SIZE", "4096")
    os.environ.setdefault("ZARRY_MAX_TOKENS", "300")
    sys.path.insert(0, str(Path(args.service_dir).resolve()))

    from app import create_app

    def loader(path, threads, context_size):
        return Llama(model_path=path, n_ctx=context_size, n_threads=threads, n_gpu_layers=0, verbose=False)

    with TestClient(create_app(model_loader=loader)) as client:
        assert client.get("/").json()["mode"] == "explanation_only"
        assert client.get("/health").status_code == 200
        ready = client.get("/ready")
        assert ready.status_code == 200 and ready.json()["model_loaded"] is True, ready.text

        first = cases[0]
        unauthenticated = client.post("/v1/explain", json={
            "symbol": first["symbol"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "context": first["context"],
            "expected_fields": first["expected_fields"],
            "kitty_assessment": first["kitty"],
            "task": "explain",
        })
        assert unauthenticated.status_code == 401, unauthenticated.text

        for case in cases:
            payload = {
                "symbol": case["symbol"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": case["context"],
                "expected_fields": case["expected_fields"],
                "kitty_assessment": case["kitty"],
                "task": "explain",
            }
            response = client.post(
                "/v1/explain", json=payload,
                headers={"Authorization": "Bearer " + os.environ["ZARRY_API_KEY"]},
            )
            assert response.status_code == 200, case["id"] + ": " + response.text
            result = response.json()
            assert result["symbol"] == case["symbol"], (case["id"], result)
            assert result["decision"] == case["kitty"]["decision"], (case["id"], result)
            assert result["authority"] == "KITTY_DETERMINISTIC_ENGINE", result
            assert result["mode"] == "explanation_only", result
            assert result["explanation_source"] in {"model", "deterministic_fallback"}, result
            assert result["cited_fields"] == case["expected_fields"], result
            assert result["numeric_claims"] == [], result
            assert "explanation-only" in result["summary"].lower(), result
            assert not any(char.isdigit() for char in result["summary"] + result["uncertainty"]), result
            print("API CASE PASSED", case["id"], "source", result["explanation_source"], "latency_ms", response.headers.get("X-ZARRY-Latency-Ms"), flush=True)

        metrics = client.get("/metrics", headers={"Authorization": "Bearer " + os.environ["ZARRY_API_KEY"]})
        assert metrics.status_code == 200, metrics.text

    print("ALL EIGHT AUTHENTICATED API CASES PASSED; UNAUTHENTICATED REQUEST REJECTED", flush=True)


if __name__ == "__main__":
    main()
