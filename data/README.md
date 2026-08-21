# Price data

## `prices.csv`

One row per parking lot, keyed by the lot name as it appears on the site.
It exists to replace the single unsourced rate each lot currently shows with
a verified range.

| Column | Meaning |
|--------|---------|
| `lot` | Lot name, matching `.lot-name` on the page |
| `type` | `official` or `offsite`, from the page |
| `source_url` | The operator's own site — where the figures must come from |
| `current_rate_ft` | What the site shows today |
| `current_unit` | `day`, or `5min` for the two drop-off tariffs |
| `current_is_estimate` | Whether the current figure is marked `~` |
| `from_ft_per_day` | Per-day rate when booking the **longest** stay the operator sells |
| `till_ft_per_day` | Per-day rate when booking **one day** |
| `max_bookable_days` | The longest stay the operator's booking form offers |
| `checked_on` | ISO date the operator's site was actually read |
| `notes` | Anything that does not fit — tiers, seasons, unreadable booking widget |

## Why a range

Several operators price in tiers: the longer the stay, the lower the per-day
rate. A single number cannot describe that, and multiplying one out across a
trip produces a figure that is wrong for anyone whose booking crosses a tier
boundary. A `from`–`till` range states the actual spread without pretending to
model each operator's tier table.

## How the site uses it

`tools/build-redesign.py` reads this file when it rebuilds the pages. Matching
is by **row position**, not by name: card order is identical across all seven
language editions, and a few lot names are localized (`myBUD Parking` is
`myBUD Parkolás` in Hungarian). Names are checked against the English page
only, and a mismatch there fails the build rather than silently attaching a
price to the wrong lot.

A row reaches the page only when `checked_on` is set:

| CSV state | What the lot shows |
|-----------|--------------------|
| `from` and `till`, both set | `1,500–2,400 Ft / day` plus a green checked-date marker |
| `from` and `till` equal | a single `2,200 Ft / day` plus the marker |
| only one of the two | that figure plus the marker |
| no `checked_on` | unchanged: the published rate, still marked `est.` if it was |

Price sorting keys off `from` where a row is verified, and off the existing
published figure everywhere else, so a part-filled file sorts sensibly.

`tests/static_checks.py` cross-checks the CSV against the built pages: the
number of verified rows must equal the number of `data-checked` attributes and
checked-date markers, so a row cannot go missing or appear from nowhere.

## Filling it in

Only ever from the operator's own site, and record `checked_on` when you do.
A row with no `checked_on` is treated as unverified and keeps showing the
current published rate — leave it blank rather than guessing.

Rows whose `current_unit` is `5min` are short-stay drop-off tariffs with no
daily rate at all; they stay out of the range treatment.
