# What the site measures, and how to read it in GA4

Property: **G-RD5NGYD43E**.

Nothing here fires until the reader accepts the cookie banner. Every event goes
through one helper, `window.ParkBUDTrack(name, params)`, defined inside the
consent script in the `<head>` of each page. Its first line is:

```js
if (read() !== 'granted') return false;
```

That check is not decoration. GA4's tag replays whatever is already sitting in
`dataLayer` the moment it loads, so an event pushed "harmlessly" before a
decision would be sent the instant someone later accepted. `tests/consent.spec.js`
asserts that using the filters, the sort, a lot row and a booking link produces
zero events before a decision and after a decline, and produces all of them
after an accept.

## Events

| Event | Fires when | Params beyond the common ones |
|---|---|---|
| `filter_select` | a filter is ticked | `filter_kind`, `filter_value` |
| `filter_deselect` | a filter is unticked, from the panel or its chip | `filter_kind`, `filter_value` |
| `filter_clear` | "Reset All" | — |
| `sort_change` | the sort actually changes (re-pressing the active one does not count) | `sort_by` |
| `search` | 900 ms after typing stops, if the box is not empty | `search_term` |
| `lot_expand` | a lot row is opened | `lot_id`, `lot_type`, `lot_access`, `list_position` |
| `booking_click` | **an operator's booking link is followed** | `lot_id`, `lot_type`, `lot_access`, `list_position`, `link_domain`, `link_url` |

Common params on every event:

- `page_language` — `en`, `hu`, `de`, `ro`, `sr`, `hr`, `sk`
- `results_shown` — how many lots were listed at that moment
- `active_filters` — the filters in force, pipe-separated (`official|shuttle|24h`)
- `sort_by` — on the lot events, the order the list was in when it was clicked

### Why the values are safe to group by

`filter_value` is one of eight fixed tokens — `official`, `offsite`, `walking`,
`shuttle`, `24h`, `ev`, `carwash`, `covered` — identical on all seven language
pages, so a report grouped by it does not fragment.

`lot_id` is the same idea for lots. It is a slug of the English name
(`premium-parking`, `dobro-car-parking`) written into `data-lot-id` on every
page, so the Hungarian and German pages report the same lot under the same id.
Two operators are named "Reptéri Parkolás" and "Repteri Parkolas" and collide
once accents are folded, so those two carry their domain suffix:
`repteri-parkolas-com` and `repteri-parkolas-hu`. `tests/static_checks.py`
fails the build if the ids ever drift apart between languages.

## One-time setup in GA4

**Custom parameters are not reportable until you register them.** Until you do,
the events appear in reports but every parameter reads `(not set)`.

Admin → Data display → **Custom definitions** → *Create custom dimension*, scope
**Event**, once per parameter:

| Dimension name | Event parameter |
|---|---|
| Filter kind | `filter_kind` |
| Filter value | `filter_value` |
| Active filters | `active_filters` |
| Sort by | `sort_by` |
| Lot ID | `lot_id` |
| Lot type | `lot_type` |
| Lot access | `lot_access` |
| Link domain | `link_domain` |
| Page language | `page_language` |

And two **custom metrics**, scope Event, unit Standard:

| Metric name | Event parameter |
|---|---|
| Results shown | `results_shown` |
| List position | `list_position` |

GA4 allows 50 event-scoped dimensions and 50 metrics, so this uses a fifth of
the budget. Data only starts filling a dimension from the day it is registered —
it is not backfilled, so register them before you want the numbers.

`search_term` and `link_url` do not need registering: GA4 has a built-in
`search_term` dimension, and `link_url` is best read via an exploration on
`link_domain` when you want the full URL.

Mark `booking_click` as a **key event** (Admin → Events) if you want it in the
standard reports and in any conversion column.

## The two questions this was built to answer

**Which filters do people use?**
Explore → Free form. Rows: *Filter value*. Values: *Event count*. Filter the
report to `Event name` exactly matches `filter_select`. Add *Page language* as a
second row dimension to see whether, say, German readers filter differently.

Compare against `filter_deselect` for the same value: a filter with a high
select-then-deselect ratio is one whose meaning is not landing.

**Do people click through to the operator?**
Explore → Free form. Rows: *Lot ID*. Values: *Event count*. Filter to
`Event name` exactly matches `booking_click`. Add *Link domain* if you want it
by operator site rather than by listing.

The honest denominator for that is `lot_expand` on the same `lot_id`: opening a
row and then following the link is the funnel. A lot with many expands and few
clicks is one whose detail is talking people out of it.

`list_position` is on both, so you can check the obvious confound — whether a
lot gets clicked because it is good or because it is near the top. Segment by
`sort_by` to separate "cheapest first" traffic from "nearest first".

## Changing the instrumentation

`tools/add-analytics-events.py` applied all of this to the seven built pages. It
is one-way and refuses to run twice. Further changes go directly into the pages
(or into a new script in the same shape) — see the note at the top of
`tools/apply-sidebar-filters.py` for why the pages are edited rather than
rebuilt.

Anything added here also belongs in `/privacy/` §3, which lists what is recorded.
