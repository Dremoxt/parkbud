#!/usr/bin/env python3
"""Write the parking rows on all seven pages from data/lots.csv.

    python3 tools/build-lots.py --check    # CI: fail if a page has drifted
    python3 tools/build-lots.py --write    # rebuild the pages from the tables

The tables are the source of truth. Editing a lot means editing one CSV row,
not hunting the same lot down in seven HTML files -- which is how the prices,
names and service tags drifted apart in the first place.

Only the <article class="lot"> blocks are rewritten, in place and in order.
Everything around them -- the comments, the blank lines, the rest of the page --
is left exactly as it was, so this can never quietly reformat the site.

    data/lots.csv       one row per lot: the facts, shared by every language
    data/lot-text.csv   the prose: name, location note, description, link label
    data/labels.csv     the feature vocabulary, one row per tag
    data/ui-labels.csv  the chrome: "Official", "est.", "from airport"
"""
import csv
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGS = [("en", "index.html"), ("hu", "hu/index.html"), ("de", "de/index.html"),
         ("ro", "ro/index.html"), ("sr", "sr/index.html"), ("hr", "hr/index.html"),
         ("sk", "sk/index.html")]

CHEVRON = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
           'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
           'stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>')


def table(name, key="lot_id"):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return rows, {r[key]: r for r in rows}


def esc(value):
    """For an attribute value, where a quote would end the attribute."""
    return html.escape(str(value), quote=True)


def txt(value):
    """For element content, where a bare quote is fine but a bare & is not."""
    return html.escape(str(value), quote=False)


def group_digits(n, separator):
    """1440 -> "1,440" in English, "1.440" in Hungarian, "1 440" in Slovak."""
    return "{:,}".format(int(n)).replace(",", separator)


def meta_text(lot, note, ui, code):
    """"0 km · at Terminal 2" for the terminal lots, "3 km from airport" else."""
    km = ("~" if lot["km_approx"] == "1" else "") + lot["km"]
    if lot["type"] == "official":
        head = "%s km" % km
    else:
        head = "%s km %s" % (km, ui["from_airport"][code])
    return head + (" · " + note if note else "")


def feature_spans(lot, labels, ui, code):
    out = []
    for token in filter(None, lot["features"].split("|")):
        highlighted = token.startswith("*")
        key = token.lstrip("*")
        if key == "@spaces":
            if not lot["spaces"]:
                continue
            label = "%s %s" % (group_digits(lot["spaces"], ui["thousands"][code]),
                               ui["spaces"][code])
        else:
            if key not in labels:
                raise SystemExit("%s: unknown feature %r (add it to data/labels.csv)"
                                 % (lot["lot_id"], key))
            label = labels[key][code]
        cls = "feature-tag highlight" if highlighted else "feature-tag"
        out.append((cls, label))
    return out


def verified(lot):
    """A row counts as verified only once someone recorded the date they read
    the operator's site. A number with no date behind it is not a fact."""
    return bool(lot.get("checked_on", "").strip()
                and (lot.get("from_ft_per_day", "").strip()
                     or lot.get("till_ft_per_day", "").strip()))


CHECK = ('<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
         ' stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"'
         ' aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7"/></svg>')


def price_marker(lot, ui, code):
    """The checked-on tick, or the "est." caveat while nothing is verified."""
    if verified(lot):
        when = lot["checked_on"].strip()
        return ('<span class="lot-checked" title="%s">%s%s</span>'
                % (esc(ui["verified"][code].replace("{d}", when)), CHECK, txt(when)))
    if lot["price_approx"] == "1":
        return '<span class="lot-est">%s</span>' % txt(ui["estimate"][code])
    return ""


def price_attrs(lot):
    if not verified(lot):
        return ""
    return ' data-from="%s" data-till="%s" data-checked="%s"' % (
        lot["from_ft_per_day"].strip(), lot["till_ft_per_day"].strip(),
        esc(lot["checked_on"].strip()))


def render(lot, text, labels, ui, code, position):
    name = text["name_" + code] or lot["name"]
    note = text["note_" + code]
    meta = meta_text(lot, note, ui, code)
    tags = feature_spans(lot, labels, ui, code)
    description = text["description_" + code]
    link_label = text["link_label_" + code]

    haystack = " ".join([name, meta] + [t for _, t in tags] + [description, link_label])

    lines = []
    lines.append(
        '<article class="lot" data-lot-id="%s" data-type="%s" data-access="%s"'
        ' data-features="%s" data-amount="%s" data-unit="%s" data-approx="%s"'
        ' data-km="%s"%s' % (lot["lot_id"], lot["type"], lot["access"], lot["facets"],
                             lot["price_ft"], lot["price_unit"], lot["price_approx"],
                             lot["km"], price_attrs(lot)))
    lines.append('                     data-search="%s">' % esc(haystack.lower()))
    lines.append('                <div class="lot-row">')
    lines.append('                    <div class="lot-main">')
    if lot["type"] == "official":
        lines.append('                        <span class="lot-tag official">%s</span>'
                     % txt(ui["official"][code]))
    else:
        lines.append('                        ')
    lines.append('                        <h3 class="lot-name">%s</h3>' % txt(name))
    lines.append('                        <p class="lot-meta">%s%s</p>'
                 % (txt(meta), price_marker(lot, ui, code)))
    lines.append('                    </div>')
    lines.append('                    <div class="lot-price">')
    lines.append('                        <div class="lot-total" data-total></div>')
    lines.append('                        <div class="lot-day" data-rate></div>')
    lines.append('                    </div>')
    lines.append('                    <button class="lot-toggle" type="button"'
                 ' aria-expanded="false" aria-controls="lot-body-%d"'
                 ' aria-label="%s: %s">' % (position, esc(ui["details"][code]), esc(name)))
    lines.append('                        %s' % CHEVRON)
    lines.append('                    </button>')
    lines.append('                </div>')
    lines.append('                <div class="lot-body card-body" id="lot-body-%d" hidden>'
                 % position)
    lines.append('                    <div class="card-features">')
    for cls, label in tags:
        lines.append('                        <span class="%s">%s</span>' % (cls, txt(label)))
    lines.append('                    </div>')
    lines.append('                    <p class="card-description">%s</p>' % txt(description))
    lines.append('                    <a href="%s" target="_blank" rel="noopener noreferrer"'
                 ' class="card-link">%s</a>' % (esc(lot["booking_url"]), txt(link_label)))
    lines.append('                </div>')
    lines.append('            </article>')
    return "\n".join(lines)


def main(argv):
    if len(argv) != 2 or argv[1] not in ("--check", "--write"):
        print(__doc__)
        return 2
    write = argv[1] == "--write"

    lots, _ = table("lots.csv")
    _, texts = table("lot-text.csv")
    labels, _ = table("labels.csv", key="feature_key")
    labels = {r["feature_key"]: r for r in labels}
    ui, _ = table("ui-labels.csv", key="key")
    ui = {r["key"]: r for r in ui}

    missing = [lot["lot_id"] for lot in lots if lot["lot_id"] not in texts]
    if missing:
        print("data/lot-text.csv has no row for: %s" % ", ".join(missing))
        return 1

    stale = []
    for code, rel in LANGS:
        path = os.path.join(ROOT, rel)
        src = open(path, encoding="utf-8").read()
        blocks = re.findall(r'<article class="lot".*?</article>', src, re.S)
        if len(blocks) > len(lots):
            print("%s has %d lots, data/lots.csv has only %d — remove extra HTML blocks first"
                  % (rel, len(blocks), len(lots)))
            return 1
        if not write and len(blocks) != len(lots):
            print("%s has %d lots, data/lots.csv has %d"
                  % (rel, len(blocks), len(lots)))
            return 1

        built = [render(lot, texts[lot["lot_id"]], labels, ui, code, i + 1)
                 for i, lot in enumerate(lots)]

        new_lots = built[len(blocks):]   # articles not yet in the HTML
        if blocks == built[:len(blocks)] and not new_lots:
            continue
        changed = sum(1 for a, b in zip(blocks, built) if a != b)
        stale.append((rel, changed + len(new_lots)))

        if write:
            out, at = [], 0
            for block, new in zip(blocks, built):
                found = src.index(block, at)
                out.append(src[at:found])
                out.append(new)
                at = found + len(block)
            # Insert new articles (not yet in HTML) before the rest of the file
            for new in new_lots:
                out.append("\n            " + new)
            out.append(src[at:])
            open(path, "w", encoding="utf-8").write("".join(out))

    if not stale:
        print("all %d pages match data/lots.csv" % len(LANGS))
        return 0

    if write:
        for rel, n in stale:
            print("rebuilt %-16s (%d lot(s) changed)" % (rel, n))
        return 0

    print("These pages no longer match the tables in data/. "
          "Run: python3 tools/build-lots.py --write")
    for rel, n in stale:
        print("  %-16s %d lot(s) differ" % (rel, n))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
