# Architecture rework — plan

Status: **awaiting approval.** Three open questions at the bottom; two of them
(hosting, URL scheme for lot pages) need answering before Stage 4.

## Goal

Replace seven hand-maintained 4,700-line HTML files with one set of templates
rendered from the CSV data, add a page per parking lot, serve prices in the
HTML rather than only via JavaScript, and give the site a new design.

**Out of scope:** changing hosting provider, adding a backend or database,
adding a booking engine, replacing the seven languages, and re-verifying the
parking prices themselves (that is data work, blocked separately on egress).

## What I read

`index.html` and the six translations (structure, inline CSS/JS, JSON-LD),
`tools/build-lots.py`, `tools/build-llms-txt.py`, `tools/build-redesign.py`,
`tests/static_checks.py`, `tests/behaviour.spec.js`, `tests/consent.spec.js`,
`tests/lib/harness.js`, `data/*.csv`, `data/README.md`, `docs/analytics.md`,
`docs/research/market-survey-2026-08-22.md`, `.github/workflows/ci.yml`,
`sitemap.xml`, `privacy/index.html`, `404.html`, and the local workflow added
by #8 — `tools/dev.sh` and `docs/local-development.md`. No `CLAUDE.md` and no
existing ADRs, so nothing prior constrains this.

`tools/dev.sh` is the everyday entry point (`serve`, `build`, `check`, `test`,
`setup`, `hooks`) and its `build` and `check` call `build-lots.py` directly.
Stages 1 and 2 both change what those mean, so it moves with them — the
commands a person types must not change even though everything behind them
does.

### The measured problem

| | |
|---|---|
| 7 pages | 4,707 lines each, 215–220 KB, ~1.5 MB total |
| inline CSS | 56 KB × 7 = 392 KB of the same stylesheet |
| inline JS | 27 KB × 7; only the translated-strings block legitimately differs |
| lot rows | 29% of each page, already generated from `data/lots.csv` |
| the other 71% | header, nav, hero, stats, 30 service cards, directions, transport, tips, footer, 5 JSON-LD blocks — seven hand-maintained copies each |

The duplication is not theoretical. `.hero h1 { margin-bottom }` is `0.75rem`
on the English page and `1.25rem` on all six others. No one decided that; it is
copy-paste drift, and nothing in CI can see it because each page is only ever
compared against itself.

## Approach

Extend the pattern that already works. `data/lots.csv` → `tools/build-lots.py`
→ HTML is proven: it round-tripped 231 lot blocks byte-for-byte and CI enforces
it. Generalise that from "the lot rows" to "the whole site": Jinja2 templates
plus the CSVs, rendered by one `tools/build.py` into static files. Same output
kind, same hosting, same data layer, one more Python dependency.

Output moves to `dist/` and is deployed by GitHub Actions rather than committed.
At 50 lots × 7 languages the site becomes ~360 pages; committing generated HTML
would turn a one-line price fix into a 360-file diff and make every pull request
unreviewable.

**Alternative considered: a static site generator (Astro or Eleventy).** Better
at this job in the abstract — components, i18n, image pipelines, incremental
builds. Rejected because it adds an npm toolchain and a framework to a project
whose owner is two days into using git locally, to solve a problem that ~200
lines of Python and a template directory already solve. Revisit if the site
grows past parking into something with real interactivity.

**Alternative considered: keep hand-edited HTML, extract only CSS and JS.**
Cheapest, and it does remove 392 KB of duplication. Rejected because the header,
footer, hero, stats, service cards and five JSON-LD blocks stay in seven copies,
so the drift that produced `.hero h1` continues.

## Changes

Six stages. Each is independently shippable, independently revertible, and
delivers something on its own.

### Stage 1 — Templates, byte-identical output

Behaviour-preserving. Nothing a visitor can see changes.

| Path | Action | What |
|---|---|---|
| `src/templates/base.html.j2` | create | `<head>`, header, nav, language picker, footer, consent banner |
| `src/templates/home.html.j2` | create | hero, stats, results, services, directions, transport, tips |
| `src/templates/privacy.html.j2` | create | from `privacy/index.html` |
| `src/templates/404.html.j2` | create | from `404.html` |
| `src/templates/partials/lot-row.html.j2` | create | the `<article class="lot">` block, ported from `build-lots.py:render()` |
| `src/templates/partials/service-card.html.j2` | create | one of the 30 service cards |
| `src/assets/site.css` | create | the 56 KB stylesheet, once, with the `.hero h1` drift resolved to the English value |
| `src/assets/site.js` | create | the page runtime, once; translated strings injected per page |
| `src/assets/consent.js` | create | the consent gate, once |
| `data/services.csv` | create | the 30 service cards lifted out of the HTML, per language |
| `data/strings.csv` | create | every remaining UI string, 7 columns |
| `tools/extract-site.py` | create | one-time lift of the above out of the HTML, same shape as `extract-lots.py` |
| `tools/build.py` | create | renders every page from templates + CSVs |
| `tools/build-lots.py` | delete | superseded; its `render()` becomes the lot-row template |
| `tools/build-redesign.py` | delete | already marked superseded, reads a CSV that no longer exists |
| `tests/static_checks.py` | modify | point `check_verified_prices` and friends at `dist/` |
| `tools/dev.sh` | modify | `build` and `check` call `build.py`; the commands people type stay the same |
| `docs/local-development.md` | modify | add the one new prerequisite, `pip install jinja2` |
| `.github/workflows/ci.yml` | modify | `build.py --check` replaces `build-lots.py --check` |

**Acceptance:** `tools/build.py` output diffed against the current seven pages
is empty apart from the `.hero h1` fix. That is the same bar the CSV extraction
met and it is what proves nothing was lost.

**Rollback:** revert the PR. The committed HTML is still the published site
until Stage 2.

### Stage 2 — Deploy from Actions

| Path | Action | What |
|---|---|---|
| `.github/workflows/deploy.yml` | create | build on push to `main`, publish `dist/` with `actions/deploy-pages` |
| `.gitignore` | modify | ignore `dist/` |
| `index.html`, `{hu,de,ro,sr,hr,sk}/index.html`, `privacy/`, `404.html` | delete | now generated |
| `tools/dev.sh` | modify | `serve` serves `dist/`, and runs `build` first so the folder exists |
| `docs/local-development.md` | modify | the loop becomes edit → build → serve; nothing is committed but sources |
| `repo settings` | manual | Pages source: "GitHub Actions" instead of "deploy from branch" |

**Verification:** deploy to a preview first; confirm all 8 current URLs return
200 and the rendered HTML matches what `main` serves today.

**Rollback:** flip Pages back to "deploy from branch"; the previous commit still
has the HTML. This is the one stage with a settings change, so it ships alone.

### Stage 3 — Data model

No new pages; new columns only, all optional, all empty until filled.

| Path | Action | What |
|---|---|---|
| `data/lots.csv` | modify | add `address`, `postcode`, `city`, `lat`, `lon`, `phone`, `site_languages`, `rating`, `review_count`, `opening_hours` |
| `data/prices.csv` | create | tiered prices: `lot_id`, `days`, `total_ft`, `checked_on`, `source_url` — one row per published tier, replacing the flat `price_ft` for lots that have real tiers |
| `data/README.md` | modify | document all of it |
| `tools/build.py` | modify | render the new fields where present, fall back where absent |
| `tests/static_checks.py` | modify | a lot with tier rows must show a range; a lot without keeps its `est.` marker |

The survey found six different pricing shapes and almost none is a flat daily
rate. A tier table is what the operators actually publish and what a reader
needs to compare their own trip length.

**Rollback:** revert; the columns are additive and unread by the old build.

### Stage 4 — A page per lot

| Path | Action | What |
|---|---|---|
| `src/templates/lot.html.j2` | create | address, map link, phone, tier table, services, languages, booking link |
| `tools/build.py` | modify | render `/parking/<lot_id>/` and `/<lang>/parking/<lot_id>/` |
| `src/templates/partials/lot-row.html.j2` | modify | row title links to the detail page |
| `tools/build-sitemap.py` | create | generate `sitemap.xml` from the routes, replacing the hand-written one |
| `tests/static_checks.py` | modify | every lot page reachable, hreflang complete, JSON-LD parses |
| `tests/behaviour.spec.js` | modify | hub → lot page → back |

~360 pages at 50 lots. All generated, none reviewed by hand.

**Rollback:** revert. New URLs 404 again, which is the state today, so nothing
that was indexed breaks.

### Stage 5 — Prices in the HTML

The survey's strongest finding: no price appears as rendered text in the served
HTML, only as a `data-amount` attribute, while the badge claims 33 were checked.

| Path | Action | What |
|---|---|---|
| `src/templates/partials/lot-row.html.j2` | modify | write the formatted price at build time; JS only re-renders on sort/filter |
| `src/templates/lot.html.j2` | modify | full tier table as real markup |
| `tools/build.py` | modify | `Product`/`Offer` JSON-LD per lot from the tier data |
| all templates | modify | correct the "from 1,600 Ft/day" claim in meta descriptions and FAQ JSON-LD |
| `tests/static_checks.py` | modify | assert a price is present as text with JS disabled |

**"from 1,600 Ft/day" is wrong today** and does not depend on any of this — it
is a marginal from-day-2 rate presented as an entry price, and the cheapest real
single day at BUD is 4,990 Ft. Fix it in Stage 1 if you want it out sooner.

### Stage 6 — Redesign

Last, because by now there is one stylesheet and one set of templates, so a
redesign is a CSS change plus template edits rather than seven-file surgery.
Scope to be agreed separately; the existing identity ("Aviation Authority",
2 PRs old) can stay or go.

## Risks

**Breakage.** The eight live URLs must keep working — enforced by an explicit
check in Stage 2 before the Pages source flips. Stage 4 adds URLs but changes
none. `llms.txt`, `robots.txt`, `CNAME`, the favicons and `og-image.jpg` are
static files that must be copied into `dist/` verbatim; a missing `CNAME` would
drop the custom domain, so that is asserted in CI, not assumed.

**Security & privacy.** No new data collected, no new third-party code, no
secrets. The consent gate and GA4 events move from inline `<script>` to
`consent.js` and `site.js` — the gate's behaviour must not change, and
`tests/consent.spec.js` already proves it three ways (nothing before a decision,
nothing after a decline, everything after an accept). External assets stay
self-hosted; no CDN is introduced. Stage 4 publishes operator phone numbers and
addresses, which are business contact details already public on the operators'
own sites — not personal data. No security-auditor escalation needed, but the
consent suite is a merge gate on Stages 1 and 2.

**Data & migrations.** No database. The CSV migrations in Stage 3 are additive:
new columns, empty defaults, old rows valid unchanged. `data/prices.csv` is new
and read only when rows exist for a lot, so a partial fill is a valid state — a
lot with tiers shows a range, a lot without keeps `price_ft` and its `est.`
marker. Down-path for every stage is `git revert`; no state lives outside the
repo.

**Operational.** Deployment changes from "Pages serves the branch" to "Actions
builds and deploys". New failure mode: a broken build blocks publishing. Mitigated
by the same checks running on the PR, so `main` is only reached by a commit that
already built. Build time at ~360 pages should stay under 10 s in Python; if it
does not, that is a signal to reconsider the SSG. Page weight should drop
sharply — the 56 KB stylesheet becomes one cacheable file instead of being
inlined in every page.

## Test strategy

The three suites already exist and stay the gate. What each stage adds:

- **Round-trip (Stage 1, unit).** Render every page from the templates and diff
  against the current committed HTML. Expected difference: the `.hero h1` fix
  and nothing else. This is the acceptance test for the whole stage.
- **Live URLs (Stage 2, e2e).** All 8 existing URLs return 200 from the built
  `dist/` before the Pages source changes; `CNAME`, `robots.txt`, `llms.txt`
  and the icons are present in the output.
- **Partial data (Stage 3, unit).** A lot with tier rows renders a range and a
  checked-on date; a lot with none keeps its published rate and `est.`; a lot
  with tiers but no `checked_on` renders as unverified — the rule that a number
  without a date is not a fact must survive the schema change.
- **Lot pages (Stage 4, integration + e2e).** Every `lot_id` has a page in all
  seven languages; hreflang on each names all seven; sitemap covers every route
  and every entry resolves to a file; hub row links to the detail page and back.
- **No-JS prices (Stage 5, e2e).** With JavaScript disabled, a price is visible
  as text on the hub and on a lot page. This is the check that would have caught
  the current defect.
- **Regression, every stage.** `tests/behaviour.spec.js` (361 checks) and
  `tests/consent.spec.js` (137 checks) unchanged and green on all seven
  languages.

New infrastructure: none. `tests/lib/server.js` already serves a directory on an
ephemeral port; it points at `dist/` instead of the repo root.

## Open questions

1. **Hosting.** "Stay on GitHub Pages, free" was not among the constraints you
   confirmed. Nothing in this plan needs a server, so **I recommend staying on
   Pages** — Stage 2 deploys to it from Actions, which is the standard path. If
   you are considering moving (Cloudflare Pages, Netlify), say so now: it changes
   Stage 2 only, but it changes it entirely. *Blocks Stage 2.*

2. **URL scheme for lot pages.** `/parking/budcar-parking/` and
   `/hu/parking/budcar-parking/`, or localised segments
   (`/hu/parkolas/budcar-parking/`)? Localised paths read better and rank
   marginally better in-language; a single segment is simpler and the slug is an
   operator's name, which is not translated anyway. **Recommend the single
   segment.** *Blocks Stage 4.*

3. **Redesign scope.** You asked for a new look and feel, but the current
   identity is two PRs old. Is Stage 6 a fresh visual direction, or a refinement
   of what is there? **Recommend deciding after Stage 4**, when the lot pages
   exist and there is something real to design against. *Blocks nothing until
   Stage 6.*

Not blocking, but worth deciding early: the language mechanism is changing
(one template rendered seven times instead of seven files), while the URLs
`/hu/`, `/de/` … stay exactly as they are, because they are indexed. If you
meant something more radical by "languages can be done a different way" — for
example dropping a language, or adding one — tell me and I will fold it in.

## Decisions to record as ADRs after approval

- `0001` Jinja2 templates over a static site generator.
- `0002` Generated output deployed from Actions rather than committed to `main`.
- `0003` Tiered prices as a separate table, replacing the flat daily rate.
