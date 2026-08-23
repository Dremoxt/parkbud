---
name: testing-conventions
description: How tests are written, named, and run in this project. Use when writing tests, reproducing bugs as tests, or running the suite.
---

# Testing conventions

## Framework & layout

The suite has two halves, both of which CI runs on every push and pull request.

| | Static checks | Browser checks |
|---|---|---|
| Framework | plain Python 3 (no pytest) | Playwright driving Chromium, plain `node` (no test runner) |
| Files | `tests/static_checks.py`, plus the `--check` modes of `tools/build-lots.py` and `tools/build-llms-txt.py` | `tests/*.spec.js`, sharing `tests/lib/harness.js` and `tests/lib/server.js` |
| Run | `tools/dev.sh check` (fast, no browser) | included in `tools/dev.sh test` |

- Run the full suite with: `tools/dev.sh test`
- Run a single browser suite with: `cd tests && node behaviour.spec.js`
- One-time setup before the browser suites will run: `tools/dev.sh setup`
- Each browser suite serves the repository on its own ephemeral port via
  `tests/lib/server.js`, so there is no server to start first and no port to collide on.

## Generated files are tested, not hand-edited

The parking rows on all seven language pages come from `data/lots.csv`, and `llms.txt`
comes from `index.html`. `tools/dev.sh check` fails when a page has drifted from its
source. Fix drift by editing the data and running `tools/dev.sh build` — never by
editing a generated page to make the check pass.

## What to test
- Behavior and public contracts, not private implementation details.
- Always cover: happy path, boundary values, error/failure paths.
- For a bug: write a failing test that reproduces it first, then fix.

## Quality bar
- Tests are deterministic — no dependence on order, time, network, or randomness unless seeded/mocked.
- Each test is independent and can run alone.
- One clear assertion focus per test; name the test after the behavior it checks.
- Prefer a few meaningful tests over many shallow ones. Coverage follows from testing the right things.

## Mocking
- Mock external systems (network, clock, filesystem) at the boundary.
- Don't mock the thing you're testing.

## Reporting
- When the suite runs, surface only failures and their causes; keep verbose output out of the main conversation.
