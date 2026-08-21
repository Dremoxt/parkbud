# Tests

The site is static HTML with no build step, so these checks run against the
files as they will be served. CI runs all of them on every pull request
(`.github/workflows/ci.yml`).

## What each suite covers

| Suite | Needs a browser | Covers |
|-------|-----------------|--------|
| `static_checks.py` | no | Markup nesting, local references resolving, `rel=noopener` on external links, JSON-LD parsing, analytics staying out of the markup, counters matching card counts, hreflang, sitemap, manifest, stripped accents |
| `behaviour.spec.js` | yes | Filters and their interaction with the show-all cap, reset, the transport bar keeping its language, the mobile menu, in-page navigation, horizontal overflow at phone widths |
| `consent.spec.js` | yes | Nothing tracker-shaped loads or sets a cookie before consent; declining persists; accepting injects both tags; the footer control reopens the banner and withdrawal works |

`tools/build-llms-txt.py --check` also runs in CI. `llms.txt` is generated
from `index.html`, so editing parking or service cards without regenerating it
fails the build — that drift is how the two fell out of sync before.

## Running locally

```sh
python3 tests/static_checks.py      # no browser needed

cd tests
npm ci
npx playwright install chromium     # once
npm test                            # behaviour + consent
```

Each browser suite serves the repository itself on an ephemeral port, so
there is nothing to start first and no port to collide with. Set `BASE_URL`
to run against something already serving the files instead, and
`CHROMIUM_PATH` to point at a Chromium that Playwright did not install.

They also block every request that does not go to the local server. That keeps runs
fast and offline-safe, and it means no assertion depends on Google or
Contentsquare being reachable — requests still fire their events, so "nothing
was requested before consent" stays a real check.

## After changing parking or service cards

```sh
python3 tools/build-llms-txt.py     # regenerate, then commit llms.txt
```
