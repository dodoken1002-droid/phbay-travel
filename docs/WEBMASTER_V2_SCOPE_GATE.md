# Webmaster V2 Scope Gate

Webmaster V2 uses an explicit path allowlist named `ALLOWED_PATHS` to define the files a worker may change.

If a requested or detected file is outside `ALLOWED_PATHS`, the worker must stop.

Scope is checked before review and checked again after review. The worker must never merge directly to `main`.
