# Editing the parking data

These CSVs are the source of truth. The parking rows on all seven language
pages are written from them by `tools/build-lots.py`, and CI fails if a page
and the tables disagree — so a lot is changed here, in one place, not in seven
HTML files.

## To change something

1. Edit the CSV. On github.com, open the file and press the pencil — GitHub
   shows CSVs as a table. Or open it in Excel or Numbers and save as CSV.
2. Run `python3 tools/build-lots.py --write`.
3. Commit both the CSV and the changed HTML.

Working from a clone instead of github.com — edit, preview the change in a
browser, run the checks, push once it looks right — is described in
[`docs/local-development.md`](../docs/local-development.md).

If you edit the CSV and forget step 2, CI tells you and prints the command.
If you edit the HTML by hand, CI tells you that too — your edit would be
overwritten the next time anyone runs the build, so it belongs in the CSV.

## lots.csv — one row per parking lot

The facts, shared by every language.

| Column | Meaning |
|---|---|
| `lot_id` | Permanent id. **Never change it** — analytics reports are grouped by it, so renaming one splits its history in two. |
| `name` | Fallback name. The name actually shown comes from `lot-text.csv`. |
| `type` | `official` (BUD's own car parks) or `offsite`. Drives the "Official" badge and the type filter. |
| `access` | `walking` or `shuttle`. Drives the access filter. |
| `km` | Distance from the terminal. Sorting by distance reads this. |
| `km_approx` | `1` prints "~3 km" instead of "3 km". |
| `price_ft` | The rate as the operator publishes it, in forints. |
| `price_unit` | `day` or `5min`. A `5min` tariff has no daily rate, so it sorts last. |
| `price_approx` | `1` prints "~" on the price and the "est." caveat. |
| `spaces` | Capacity, digits only. Shown where the row's `features` contains `@spaces`. |
| `facets` | What the **filters** match: any of `24h,ev,carwash,covered`, comma-separated. |
| `features` | What the reader **sees**, pipe-separated keys from `labels.csv`. `*` marks the highlighted first tag; `@spaces` prints the capacity. |
| `booking_url` | Where "Book Now" goes. |

`facets` and `features` are deliberately separate: the filter needs a fixed
vocabulary of four, the badges are free to say "🔒 CCTV 24/7".

### Verified prices

| Column | Meaning |
|---|---|
| `source_url` | The page you read the price on. |
| `from_ft_per_day` | Per-day rate at the **longest** bookable stay. |
| `till_ft_per_day` | Per-day rate for a **single** day. |
| `max_bookable_days` | The longest stay the operator's form allows. |
| `checked_on` | `YYYY-MM-DD`, the day you read it. |
| `notes` | Anything worth remembering. Never shown. |

A row shows a price range only once `checked_on` is filled in **and** at least
one of from/till has a number. Until then the lot keeps its `price_ft` with the
"est." caveat. That rule is enforced by a test: a number with no date behind it
is not a fact, and the site should not present it as one.

Fill these in and the row switches from "~1,700 Ft est." to "1,500–2,200 Ft"
with a checked-on tick — no other change needed.

## lot-text.csv — the words, per language

`name_xx`, `note_xx`, `description_xx`, `link_label_xx` for each of
`en hu de ro sr hr sk`.

`note_xx` is the part after the "·" — "Vecsés, Üllői út", "at Terminal 2
(1 min walk)". The "3 km from airport" in front of it is generated, so it does
not belong here.

Leave a name blank and `lots.csv`'s `name` is used instead. Company names
should be identical in every column: myBUD Parking is called myBUD Parking in
Slovak too.

## labels.csv — the feature vocabulary

One row per badge, translated seven ways. Add a row here before using a new key
in `features`; the build fails on an unknown key rather than printing a blank
badge.

Keep it small. Every distinct row is a phrase a reader has to tell apart from
the others — "🔒 Secured", "🔒 Guarded" and "🔒 Monitored" are three rows that
probably want to be one.

## ui-labels.csv — the chrome

The words around every lot: the "Official" badge, "est.", "from airport",
"Spaces", the thousands separator, and the checked-on tooltip. Seven columns,
six rows. Changing "from airport" here changes it on 231 lot rows at once —
which is how it got fixed after sitting there in English on all six translated
pages.

## Where the ids come from

`lot_id` also appears in the page as `data-lot-id` and is what GA4 reports are
grouped by (see `docs/analytics.md`). A static check fails the build if the ids
ever differ between language pages.
