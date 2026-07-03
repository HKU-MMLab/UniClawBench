"""Small utilities shared across runner / supervision / scripts.

Files under this package are intentionally narrow — each owns a single
concept that didn't fit naturally inside the runner / supervision /
proxy domains.  Anything that grows beyond ~300 lines or starts to
acquire cross-cutting state belongs in its own subpackage.
"""
