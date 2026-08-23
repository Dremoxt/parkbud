# Project guide for Claude Code

This project uses a small team of subagents. This file defines when each one is used so the workflow stays consistent across sessions.

## The team

| Agent | Role | Can edit code? |
| --- | --- | --- |
| `architect` | Plans non-trivial work before code is written | No (read-only) |
| `designer` | Designs UX/UI for user-facing pages and flows | No (read-only) |
| `implementer` | Writes and modifies code from a plan | Yes |
| `code-reviewer` | Reviews quality, readability, performance | No (read-only) |
| `security-auditor` | Audits security, secrets, privacy, deps | No (read-only) |
| `test-engineer` | Writes and runs tests | Yes |
| `doc-writer` | Writes and updates documentation | Yes |

## Default workflow

For any non-trivial feature, refactor, or bug fix, follow this order. Skip steps only for genuinely trivial changes (typos, one-line fixes).

1. **Plan** — delegate to `architect`. Get a written plan and confirm it with me before coding.
2. **Design** — if the change adds or alters user-facing UI (pages, forms, tables, dashboards, any CRUD surface), delegate to `designer`. Get a written design spec and confirm it with me before implementation. The designer follows the `saas-crud-ux` skill.
3. **Implement** — delegate to `implementer`, one focused change at a time. For UI work, the implementer builds to the confirmed design spec.
4. **Test** — delegate to `test-engineer` to add/run tests. Code isn't done until tests are green.
5. **Review** — delegate to `code-reviewer`. Apply Critical and Warning findings. For UI changes, the review includes checking the result against the design spec (states, accessibility, responsive behavior).
6. **Security** — if the change touches auth, user data, external input, dependencies, or config, delegate to `security-auditor` before merging.
7. **Document** — delegate to `doc-writer` for any user-facing or API change.
8. **Update ticket** — if the work belongs to a Linear issue, update that issue's description (via the Linear MCP) with a summary of what was implemented **from the user's perspective**: what the user can now do or see, not implementation details. Append it under a heading like "What shipped" rather than overwriting the original requirement. Do this only after tests are green.

## Standing rules

- Never commit secrets. Configuration comes from environment variables. `.env` is gitignored.
- Reviewers, the auditor, and the designer are read-only by design — do not grant them write access to "save a step."
- Prefer the smallest change that works, with a clear rollback path. Stability over cleverness.
- When a requirement is ambiguous, stop and ask rather than guessing.
- The shared skills (`coding-standards`, `security-checklist`, `testing-conventions`, `saas-crud-ux`) are the source of truth for conventions. Keep them updated as the project evolves.
- UI work is never "done" without empty, loading, and error states, keyboard access, and the anti-pattern check from `saas-crud-ux`.
