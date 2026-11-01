"""Download the pinned ZARRY GGUF model into persistent local storage."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

DEFAULT_REPO = "unsloth/Qwen3-1.7B-GGUF"
DEFAULT_PATTERN = "Qwen3-1.7B-Q4_K_M.gguf"
DEFAULT_REVISION = "b2d17796e6fd93c353a0415a3abd8b7f801701de"
OBSOLETE_REPO = "unsloth/SmolLM3-3B-GGUF"


def resolve_cache_dir(environ: dict[str, str] | None = None) -> Path:
    """Resolve the actual Hugging Face cache root, including Railway volume defaults."""
    env = os.environ if environ is None else environ
    explicit = env.get("HF_HOME") or env.get("HF_HUB_CACHE")
    if explicit:
        return Path(explicit)
    volume_mount = env.get("RAILWAY_VOLUME_MOUNT_PATH")
    if volume_mount:
        return Path(volume_mount) / "hf-cache"
    return Path.home() / ".cache" / "huggingface" / "hub"


def cache_diagnostics(cache_dir: str | Path) -> dict[str, int | bool]:
    """Return non-secret disk/cache diagnostics for deployment logs."""
    root = Path(cache_dir)
    usage = shutil.disk_usage(root)
    smol = root / "models--unsloth--SmolLM3-3B-GGUF"
    qwen = root / "models--unsloth--Qwen3-1.7B-GGUF"
    nested_smol = root / "hub" / "models--unsloth--SmolLM3-3B-GGUF"
    return {
        "free_bytes": usage.free,
        "smol_cache_present": smol.exists() or nested_smol.exists(),
        "qwen_cache_present": qwen.exists() or (root / "hub" / qwen.name).exists(),
    }


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


def clear_incomplete_model_downloads(cache_dir: str | Path | None, repo_id: str) -> int:
    """Delete only interrupted partial files for the selected model; keep completed blobs."""
    if not cache_dir:
        return 0
    repo_cache_name = "models--" + repo_id.replace("/", "--")
    roots = (Path(cache_dir) / repo_cache_name, Path(cache_dir) / "hub" / repo_cache_name)
    removed = 0
    for root in roots:
        blobs = root / "blobs"
        if blobs.exists():
            for partial in blobs.glob("*.incomplete"):
                partial.unlink()
                removed += 1
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
    cache_dir = resolve_cache_dir()
    revision = os.getenv("ZARRY_MODEL_REVISION", DEFAULT_REVISION).strip() or DEFAULT_REVISION

    print(f"ZARRY_CACHE_DIR={cache_dir}", file=sys.stderr, flush=True)
    print(f"ZARRY_CACHE_BEFORE={cache_diagnostics(cache_dir)}", file=sys.stderr, flush=True)
    if clear_obsolete_model_cache(cache_dir, repo_id):
        print(f"Removed obsolete model cache for {OBSOLETE_REPO}")
    removed_partials = clear_incomplete_model_downloads(cache_dir, repo_id)
    if removed_partials:
        print(f"Removed {removed_partials} interrupted partial Qwen download file(s)", file=sys.stderr, flush=True)
    print(f"ZARRY_CACHE_AFTER={cache_diagnostics(cache_dir)}", file=sys.stderr, flush=True)

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
