---
name: coding-standards
description: The project's coding conventions — naming, structure, error handling, logging, and dependency rules. Use when writing, reviewing, or refactoring code in this project.
---

# Coding standards

> The sections below are language-agnostic defaults; the stack-specific parts are filled
> in for this project. Keep them current as the project evolves.

## This project's shape

A static, multilingual site — no framework, no build step, no runtime server. Plain
HTML/CSS/JS served as files, with Python 3 scripts under `tools/` generating the parts
that must stay in sync.

- **Never hand-edit generated content.** The parking rows on the seven language pages
  are written from `data/lots.csv`; `llms.txt` is written from `index.html`. Edit the
  source, then run `tools/dev.sh build`. Editing a page directly is how prices, names
  and service tags drifted apart before, and CI now fails on it.
- Keep the seven language pages structurally parallel. A change to one is usually a
  change to all seven.
- Generator scripts are standard-library Python 3 — no third-party runtime deps. Keep it
  that way; `tests/` is the only place with a dependency (Playwright).

## Naming & structure
- Use descriptive names; avoid abbreviations except well-known ones (id, url, db).
- One responsibility per function/module. If you can't name it clearly, it's doing too much.
- Keep files focused. Group by feature, not by layer, unless the project already does otherwise.

## Error handling
- Fail loudly at boundaries, degrade gracefully in the core. Never swallow errors silently.
- Return or raise typed/specific errors, not generic ones. Include enough context to debug.
- Validate external input (user, network, file) before trusting it.

## Configuration & secrets
- No secrets in source. Read from environment variables or a secrets manager.
- No environment-specific values hardcoded (URLs, ports, paths).

## Logging
- Log decisions and failures, not noise. Never log secrets, tokens, or full PII.
- Use structured logging with consistent levels (debug/info/warn/error).

## Dependencies
- Prefer the standard library. Add a dependency only when it clearly pays for itself.
- Before adding one: check it's maintained, widely used, and its license is compatible with this project.

## Formatting & lint
- No formatter or linter is configured. The gate is `tools/dev.sh check` — run it before
  every commit. `tools/dev.sh hooks` installs a pre-push hook that enforces it.
- `tests/static_checks.py` is the closest thing to a linter here: it checks markup,
  internal references, the sitemap and the web manifest. Extend it rather than adding a
  new tool.
