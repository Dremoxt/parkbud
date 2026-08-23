#!/usr/bin/env bash
# Local development for the Budapest Airport parking guide.
#
# The site is static HTML with no build step, so "running it locally" is just
# serving the repository. The parts that are generated — the parking rows on
# the seven language pages and llms.txt — have to be rebuilt after a data or
# card edit, and the same checks CI runs are runnable here before pushing.
#
#   tools/dev.sh serve    open the site at http://localhost:8000
#   tools/dev.sh build    regenerate the parking rows and llms.txt
#   tools/dev.sh check    the checks CI runs without a browser (fast)
#   tools/dev.sh test     check + the Playwright suites (slower)
#   tools/dev.sh setup    install the test dependencies and Chromium (once)
#   tools/dev.sh hooks    refuse `git push` while the checks fail
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT="${PORT:-8000}"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }

usage() {
  cat <<'TXT'
Local development for the Budapest Airport parking guide.

  tools/dev.sh serve    open the site at http://localhost:8000
  tools/dev.sh build    regenerate the parking rows and llms.txt
  tools/dev.sh check    the checks CI runs without a browser (fast)
  tools/dev.sh test     check + the Playwright suites (slower)
  tools/dev.sh setup    install the test dependencies and Chromium (once)
  tools/dev.sh hooks    refuse `git push` while the checks fail

PORT=3000 tools/dev.sh serve  serves on another port.
See docs/local-development.md for the whole workflow.
TXT
  exit "${1:-0}"
}

cmd_serve() {
  say "Serving $ROOT at http://localhost:$PORT  (Ctrl-C to stop)"
  echo "Language pages: /hu/ /de/ /ro/ /sr/ /hr/ /sk/"
  exec python3 -m http.server "$PORT"
}

cmd_build() {
  say "Writing the parking rows from data/*.csv"
  python3 tools/build-lots.py --write
  say "Regenerating llms.txt from index.html"
  python3 tools/build-llms-txt.py
  echo
  git --no-pager diff --stat || true
}

cmd_check() {
  say "Parking rows match data/lots.csv"
  python3 tools/build-lots.py --check
  say "llms.txt is in sync with index.html"
  python3 tools/build-llms-txt.py --check
  say "Markup, references, sitemap and manifest"
  python3 tests/static_checks.py
  say "Static checks passed."
}

cmd_test() {
  cmd_check
  if [ ! -d tests/node_modules ]; then
    echo
    echo "Browser suites skipped: tests/node_modules is missing."
    echo "Run 'tools/dev.sh setup' once to install them."
    return 1
  fi
  say "Filters, navigation and responsive layout"
  ( cd tests && node behaviour.spec.js )
  say "Analytics consent gate"
  ( cd tests && node consent.spec.js )
  say "Everything CI runs has passed locally."
}

cmd_setup() {
  say "Installing test dependencies"
  ( cd tests && npm ci )
  say "Installing Chromium for Playwright"
  ( cd tests && npx playwright install chromium )
  say "Done. 'tools/dev.sh test' now runs the browser suites too."
}

cmd_hooks() {
  local hook=".git/hooks/pre-push"
  cat > "$hook" <<'HOOK'
#!/usr/bin/env sh
# Installed by tools/dev.sh hooks. Runs the checks CI runs before letting a
# push through, so a red build is caught here rather than on GitHub.
# To push anyway: git push --no-verify
if [ -d tests/node_modules ]; then
  exec tools/dev.sh test
else
  exec tools/dev.sh check
fi
HOOK
  chmod +x "$hook"
  say "Installed $hook — 'git push' now runs the checks first."
  echo "Remove it with: rm $hook"
}

case "${1:-}" in
  serve) cmd_serve ;;
  build) cmd_build ;;
  check) cmd_check ;;
  test)  cmd_test ;;
  setup) cmd_setup ;;
  hooks) cmd_hooks ;;
  ""|-h|--help|help) usage 0 ;;
  *) echo "Unknown command: $1" >&2; usage 1 ;;
esac
