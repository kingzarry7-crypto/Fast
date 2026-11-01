"""Download the pinned ZARRY GGUF model into persistent local storage."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

DEFAULT_REPO = "unsloth/Qwen3-1.7B-GGUF"
DEFAULT_PATTERN = "Qwen3-1.7B-Q4_K_M.gguf"
DEFAULT_REVISION = "b2d17796e6fd93c353a0415a3abd8b7f801701de"
OBSOLETE_REPO = "unsloth/SmolLM3-3B-GGUF"


def clear_obsolete_model_cache(cache_dir: str | Path | None, repo_id: str) -> bool:
    """Remove only the previous SmolLM3 repository cache after selecting another model."""
    if not cache_dir or repo_id == OBSOLETE_REPO:
        return False
    cache_root = Path(cache_dir)
    obsolete_paths = (
        cache_root / "models--unsloth--SmolLM3-3B-GGUF",
        cache_root / "hub" / "models--unsloth--SmolLM3-3B-GGUF",
    )
    removed = False
    for obsolete in obsolete_paths:
        if obsolete.exists():
            shutil.rmtree(obsolete)
            removed = True
    return removed


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
    cache_dir = os.getenv("HF_HOME") or None
    revision = os.getenv("ZARRY_MODEL_REVISION", DEFAULT_REVISION).strip() or DEFAULT_REVISION

    if clear_obsolete_model_cache(cache_dir, repo_id):
        print(f"Removed obsolete model cache for {OBSOLETE_REPO}")

    snapshot = snapshot_download(
        repo_id=repo_id,
        allow_patterns=[pattern],
        cache_dir=cache_dir,
        revision=revision,
    )
    model_path = resolve_model_file(snapshot, pattern)
    print(f"ZARRY_MODEL_REPO={repo_id}")
    print(f"ZARRY_MODEL_REVISION={revision}")
    print(f"ZARRY_MODEL_PATH={model_path}")


if __name__ == "__main__":
    main()
