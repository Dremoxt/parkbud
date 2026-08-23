# Review notes on the 22 Aug 2026 market survey

Written against `market-survey-2026-08-22.md`. Nothing in `data/` has been
changed. This is the working brief for when we do act.

## One finding in the survey is wrong

**§3.8 "Filters that cannot fire"** — the filters do work. The survey's crawler
did not run JavaScript, so it saw the unpopulated markup. In a browser the
counts read Official 5 · Off-Site 28 · Walking 5 · Shuttle 28 · 24/7 33 ·
EV 4 · Car Wash 3 · Covered 7, and `tests/behaviour.spec.js` asserts on every
language page that ticking "Official" narrows the list to 5 and that the apply
button names the count. Worth knowing before anyone spends a day on a non-bug.

## Two findings are right, and one of them is the important one

**§3.1 prices are not in the served HTML — correct, and this is the finding to
act on.** Each row ships `<div class="lot-total" data-total></div>`, empty, and
`renderPrices()` fills it. The number *is* present as `data-amount="2500"` on
the article, so a determined scraper can get it, but no price appears as
rendered text. For a search engine, an AI crawler, or a reader with JS off,
this site publishes no prices at all — while claiming in its own badge that 33
of them were checked yesterday. Fixing this is a build-time change: the
generator already has `price_ft`, so it can write the formatted price into the
markup and let the script take over only when a range is present.

**§3.7 coverage — right, and larger than stated.** The survey lists ~50
entries against our 33. Confirmed absent and notable: Hispania (4,145 reviews,
the highest-volume lot at BUD), MoPark, Airport Parking Hungary, Park & Bark,
Pocket Parking (2.6 km — closer than anything we list), ABC Gold, Hotel
Ferihegy (cheapest single day at 4,990), Star Park, Ferihegy Top, Union,
Park & Rent, IQ, ZEN, Csendes, PárnaPig, Null Terminál.

## The live inaccuracy to fix first

"**from 1,600 Ft/day**" is hard-coded in meta descriptions and FAQ JSON-LD:
6 occurrences in `index.html`, 3 in each translation, 2 in `llms.txt`. It comes
from the cheapest `price_ft` in our own table (Repteri Parkolas, 1,600) — and
the survey shows that whole column is the wrong quantity. The cheapest real
single day at BUD is 4,990. We are advertising a marginal from-day-2 rate as an
entry price, in structured data that Google may show as a rich result.

This is not gated on any schema work: the claim is wrong today and can be
corrected today.

## The schema does not fit the market

`price_ft` + `price_unit=day` assumes one flat daily rate. The survey shows the
real shape is almost always **first day, then a marginal rate**, or a **quoted
total per N days**:

| Shape | Example |
|---|---|
| first day + marginal | Budapest Reptér Parkoló 9,900 then +1,000/day |
| first day + marginal | Star Park 5,900 then +1,000/day |
| marginal only from day 2 | Best Parking +700/day outdoor, +1,700 covered |
| flat band | Európa 12–24 days flat 24,000; Comfort 1–3 days all 10,000 |
| true daily rate | Ferihegy Parking 1,200/day + 2,500/transfer |
| per period started | official zones: 6–30 min, 31–60 min, 2 h, 3 h, 5 h, +day |

`from_ft_per_day` / `till_ft_per_day` were built for exactly this and are still
empty. They express the envelope (cheapest per-day at max stay → most expensive
at one day) without claiming a tier table we do not hold. The survey's 1-day
and 7-day columns populate both ends directly:
`till = 1-day total`, `from ≈ 7-day total / 7` — or better, the published
per-day marginal where the operator states one.

Open question for you: whether to keep the envelope, or move to a real tier
table (`1d, 2d, 3d, 7d, 10d, 30d, +extra`) which is what ParkoLow publishes and
what would actually let a reader compare their own trip length.

## Category standardisation — what the survey implies

Today: 4 filter facets (`24h`, `ev`, `carwash`, `covered`) and 29 free-text
badge labels. The survey names service attributes that recur across operators
and would be worth making into real, filterable categories:

**Security** guarded 24/7 · CCTV · fenced/walled · alarm · armed guards ·
licence-plate entry · automatic barrier
**Shelter** outdoor · covered bay · indoor hall · individual garage
**Transfer** free shuttle · on-demand vs timetabled · to Departures level vs
Arrivals · transfer charged separately · VIP transfer
**Vehicle services** car wash · valeting · EV charging (with Ft/kWh) ·
jump-start / tyre help · windscreen repair
**Traveller services** luggage wrapping · luggage weighing · child seat ·
coffee/refreshments · washroom · departure board · English-speaking staff
**Booking & payment** online booking · free cancellation · pay on arrival ·
card accepted · cash only · loyalty discount · no-show fee
**Vehicle types** oversize/van · bus/motorhome/boat storage · low-clearance
garage limits
**Unusual** dog boarding · on-site accommodation · keys left with staff ·
free day for late arrival / early return

That is far more than 8 checkboxes should carry. My suggestion when we get to
it: keep the *filter* facets to a small set people actually filter on, and let
the rest be displayed attributes. Which ones become filters is a product call,
not a data one — worth deciding from the GA4 `filter_select` data once it has
run a few weeks.

## Fields the table does not have and the survey does

`address` · `lat` / `lon` · `phone` · `rating` / `review_count` ·
`site_languages` · `opening_hours`. The survey is right that no address, GPS or
phone appears anywhere on the site — the three things a driver actually needs.
`site_languages` is the one it calls our biggest missed opportunity, given our
audience is exactly the RO/SR/HR/SK drivers who need to know which lots serve
them.

## Data corrections the survey supports

- **Safe Parking address.** We show "Vecsés, Széchenyi u."; the survey gives
  Üllői út 847 (postal Almáskert út 15). Széchenyi u. 153/B is Parkolómester.
- **Distances.** Twenty-plus of our rows say `~3 km`. Survey measurements:
  NOA 5.4 · Dobro 6.2 · Hungária 5.2 · Nemzeti 6.3 · Zoka 5.0 · Repteres 4.8 ·
  Sky 3.0 · Park Central 3.7. Our two *specific* off-site figures are also low:
  BUDCAR at 2 km (measured 3.7) and Comfort at 2 km (measured 4.1) — both look
  like the operator's own marketing claim copied straight in.
- **Probable duplicate.** "Ferihegy Airport Parking" (repterparkolo.hu) and
  "FAP" (fedettrepterparkolo.hu) may be one brand listed twice. Needs a look at
  both sites, which this container cannot reach.
- **Missing 6th official zone.** The Arrivals pick-up area, at 50,000 Ft for
  10–24 h, is the most expensive mistake a driver can make here and we do not
  warn about it.

## Provenance caveat

The survey's own note applies: rows marked "not verified" for languages were
not opened directly, its official-zone tariffs come from a third-party guide
rather than bud.hu, and one operator's price list is dated 2018. Anything that
reaches `data/lots.csv` needs `checked_on` and `source_url` filled in per row,
which is what the verified-price rule already enforces.
