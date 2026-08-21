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

## Filling it in

Only ever from the operator's own site, and record `checked_on` when you do.
A row with no `checked_on` is treated as unverified and keeps showing the
current published rate — leave it blank rather than guessing.

Rows whose `current_unit` is `5min` are short-stay drop-off tariffs with no
daily rate at all; they stay out of the range treatment.
