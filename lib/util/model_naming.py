"""Bidirectional naming between filesystem-safe ``model_dir`` strings and
the dotted ``provider/model`` identifier the runtime expects.

The runs tree uses dash-only directory names so every model lands in
exactly one well-known filesystem location (``runs/<backend>/<model_dir>/
<suite>/<task>/``).  The runner + API expect the canonical dotted form
(``proxy-example/gpt-5.4``).  Code on both sides of the
dispatcher needs to translate between them.

Forward (``provider/model`` → ``model_dir``) is a deterministic string
transform: replace ``/`` and ``.`` with ``-``.

Reverse (``model_dir`` → ``provider/model``) is ambiguous as a pure
string transform — both ``.`` and ``-`` in the source flatten to ``-``,
so ``qwen3.5-plus`` and ``qwen3-5.plus`` both encode to
``qwen3-5-plus``.  We resolve the ambiguity by consulting the canonical
model registry in ``configs/models.local.json``: the unique entry whose
forward-encoded form equals the input wins.

Adding a new model = add it to ``models.local.json``.  No separate
dispatch-side lookup table.
"""
from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Optional


def encode_model_dir(model_full: str) -> str:
    """Convert ``provider/model`` to the filesystem-safe dash form.

    Examples:
        ``proxy-example/gpt-5.4``      → ``proxy-example-gpt-5-4``
        ``dashscope-coding/qwen3.5-plus`` → ``dashscope-coding-qwen3-5-plus``
    """
    return model_full.replace("/", "-").replace(".", "-")


_PROVIDER_PREFIXES = (
    "provider-all-new",
    "provider-all",
    "provider-primary",
    "native-openai-proxy",
    "proxy-example",
    "proxy-usage",
    "model-provider",
    "model-router",
    "api-proxy",
    "proxy",
)

_MODEL_START_RE = None

_DISPLAY_OVERRIDES = {
    "aws.claude-sonnet-4.6": "claude-sonnet-4.6",
    "aws-claude-sonnet-4-6": "claude-sonnet-4.6",
    "aws.claude-opus-4.6": "claude-opus-4.6",
    "aws-claude-opus-4-6": "claude-opus-4.6",
    "gpt-5-4-controller": "gpt-5.4",
}


def display_model_name(model_name: str | None) -> str:
    """Return the public, provider-free model label for UI/docs surfaces.

    Runtime identifiers may include provider/key-pool prefixes or
    filesystem-safe encodings such as ``provider-primary-gpt-5-4``.  Public
    WebUI surfaces should show only the generic model name.
    """

    if not model_name:
        return ""
    label = str(model_name).strip()
    if "/" in label:
        label = label.rsplit("/", 1)[-1]
    label = label.replace("_", "-")

    # Remove provider/key-pool prefixes repeatedly; encoded run directories can
    # contain nested-looking prefixes flattened into one dash-delimited string.
    changed = True
    while changed:
        changed = False
        lower = label.lower()
        for prefix in _PROVIDER_PREFIXES:
            for sep in ("-", "."):
                token = prefix.lower().replace("_", "-") + sep
                if lower.startswith(token):
                    label = label[len(token):]
                    changed = True
                    break
            if changed:
                break

    label = _strip_to_model_token(label)

    lower = label.lower()
    if lower in _DISPLAY_OVERRIDES:
        return _DISPLAY_OVERRIDES[lower]

    return _restore_version_dots(label)


def _strip_to_model_token(label: str) -> str:
    """Drop any leading routing/key-pool text before a recognizable model id."""

    import re

    global _MODEL_START_RE
    if _MODEL_START_RE is None:
        _MODEL_START_RE = re.compile(
            r"(?i)(claude-|gpt-\d|gemini-\d|qwen\d|kimi-k\d|minimax-m\d)"
        )
    match = _MODEL_START_RE.search(label)
    if match and match.start() > 0:
        return label[match.start():]
    return label


def _restore_version_dots(label: str) -> str:
    import re

    patterns = [
        (r"^(claude-(?:opus|sonnet))-(\d+)[.-](\d+)(?:-.+)?$", r"\1-\2.\3"),
        (r"^(gpt)-(\d+)-(\d+)(?:-(mini|nano|controller))?$", _format_gpt_version),
        (r"^(gemini)-(\d+)-(\d+)-(.+)$", r"\1-\2.\3-\4"),
        (r"^(qwen\d+)-(\d+)(-.+)$", r"\1.\2\3"),
        (r"^(kimi-k\d+)-(\d+)$", r"\1.\2"),
        (r"^(minimax-m\d+)-(\d+)$", r"\1.\2"),
    ]
    for pattern, repl in patterns:
        next_label = re.sub(pattern, repl, label, flags=re.IGNORECASE)
        if next_label != label:
            return next_label
    return label


def _format_gpt_version(match) -> str:
    suffix = match.group(4)
    base = f"{match.group(1)}-{match.group(2)}.{match.group(3)}"
    if suffix and suffix.lower() != "controller":
        return f"{base}-{suffix}"
    return base


def include_in_public_webui(
    backend: str | None,
    model_name: str | None,
    category: str | None = None,
) -> bool:
    """Return whether a run belongs in the public WebUI result set.

    The public benchmark view intentionally excludes smoke-test runs and Gemini
    Pro runs for non-OpenClaw harnesses. Those cells were operational probes
    rather than part of the final comparison matrix; leaving them in makes the
    dynamic and static dashboards report a larger experiment set than the paper
    describes. OpenClaw Gemini Pro remains included.
    """

    category_norm = str(category or "").strip().lower()
    if category_norm.startswith(("000_", "001_")):
        return False

    backend_norm = str(backend or "").strip().lower()
    model_norm = display_model_name(model_name).lower().replace("_", "-")
    is_gemini_pro = model_norm.startswith("gemini-") and "-pro" in model_norm
    return not (backend_norm != "openclaw" and is_gemini_pro)


def decode_model_full(model_dir: str, registry: Iterable[str]) -> str:
    """Reverse of :func:`encode_model_dir` resolved via the registry.

    Returns the unique ``provider/model`` whose forward-encoded form
    equals ``model_dir``.  Raises ``ValueError`` if no match (unknown
    model) or more than one match (genuine collision in the registry).
    """
    candidates = [m for m in registry if encode_model_dir(m) == model_dir]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(
            f"unknown model_dir {model_dir!r}: not in registry "
            f"(add the matching provider/model to configs/models.local.json)"
        )
    raise ValueError(
        f"ambiguous model_dir {model_dir!r}: registry has multiple matches {candidates}"
    )


def load_registry(models_json_path: Path | str) -> list[str]:
    """Return ``['provider/model', ...]`` from a models.local.json file.

    Walks ``providers.<name>.models[]`` and joins each model's ``id``
    (falling back to ``name``) with its provider name.  Provider configs
    that omit ``models`` or are not dicts are silently skipped.
    """
    path = Path(models_json_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    providers = data.get("providers") or {}
    out: list[str] = []
    for provider_name, provider_cfg in providers.items():
        if not isinstance(provider_cfg, dict):
            continue
        models = provider_cfg.get("models") or []
        for entry in models:
            if isinstance(entry, dict):
                model_id = entry.get("id") or entry.get("name")
            else:
                model_id = entry
            if model_id:
                out.append(f"{provider_name}/{model_id}")
    return out


def default_models_json_path(repo_root: Optional[Path] = None) -> Path:
    """Default location of ``configs/models.local.json`` for this repo.

    ``repo_root`` defaults to two directories above this file
    (``lib/util/model_naming.py`` → ``lib/util/`` → ``lib/`` → repo).
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    return Path(repo_root) / "configs" / "models.local.json"
