"""Download the selected ZARRY GGUF model into a persistent local directory."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_REPO = "unsloth/SmolLM3-3B-GGUF"
DEFAULT_PATTERN = "*Q4_K_M.gguf"


def resolve_model_file(snapshot_dir: str | Path, pattern: str = DEFAULT_PATTERN) -> Path:
    matches = sorted(Path(snapshot_dir).glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one model file matching {pattern!r}; found {len(matches)}"
        )
    return matches[0]


def main() -> None:
    from huggingface_hub import snapshot_download

    repo_id = os.getenv("ZARRY_MODEL_REPO", DEFAULT_REPO).strip()
    pattern = os.getenv("ZARRY_MODEL_FILE_PATTERN", DEFAULT_PATTERN).strip()
    cache_dir = os.getenv("HF_HOME")
    revision = os.getenv("ZARRY_MODEL_REVISION", "").strip()
    snapshot = snapshot_download(
        repo_id=repo_id,
        allow_patterns=[pattern],
        cache_dir=cache_dir or None,
        revision=revision or None,
    )
    model_path = resolve_model_file(snapshot, pattern)
    print(f"ZARRY_MODEL_REPO={repo_id}")
    if revision:
        print(f"ZARRY_MODEL_REVISION={revision}")
    print(f"ZARRY_MODEL_PATH={model_path}")


if __name__ == "__main__":
    main()
