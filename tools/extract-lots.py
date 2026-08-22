#!/usr/bin/env python3
"""One-time lift of the parking data out of the seven HTML pages and into
data/lots.csv, data/lot-text.csv and data/labels.csv.

Run once. From then on the tables are the source of truth and
tools/build-lots.py writes the pages from them; CI runs it in --check mode so
the two cannot drift apart again.

Nothing here invents or normalises anything. Whatever the pages say today is
what lands in the tables, so the round trip (extract, then build) leaves the
HTML byte-identical. Cleaning up the data is then an edit to a CSV, reviewable
in a diff, rather than a change buried in a script.
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
CODES = [c for c, _ in LANGS]


def lots_of(rel):
    src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    return re.findall(r'(<article class="lot".*?</article>)', src, re.S)


def attr(block, name):
    m = re.search(r'\b%s="([^"]*)"' % name, block)
    return m.group(1) if m else ""


def text(block, pattern):
    m = re.search(pattern, block, re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def tags_of(block):
    """(highlighted, label) in document order."""
    return [(bool(h), html.unescape(t).strip())
            for h, t in re.findall(r'feature-tag( highlight)?">([^<]*)<', block)]


SPACES = re.compile(r"^([\d,  ]+)\s*(Spaces|Parkplätze|Parkolóhely|Locuri|"
                    r"Mesta|Mjesta|Miest|Parkirnih mjesta|Parking mesta)", re.I)


def slug_for(label):
    flat = re.sub(r"[^\w\s&/-]", " ", label, flags=re.U)      # drop the emoji
    flat = re.sub(r"[\s&/]+", "-", flat.strip()).strip("-")
    return re.sub(r"-+", "-", flat).lower()


class Keys:
    """One key per distinct English label, never one key for two of them.

    "🕐 24/7" and "🔒 24/7" slug identically but are not the same string, and
    quietly folding them together here would change what eleven lots display
    without that ever appearing in a diff. They get separate keys, and the
    near-duplicates are reported so they can be merged in the CSV instead,
    where the change is reviewable.
    """

    def __init__(self):
        self.by_label = {}
        self.taken = {}

    def key(self, label_en):
        if label_en in self.by_label:
            return self.by_label[label_en]
        base = slug_for(label_en)
        key, n = base, 1
        while key in self.taken:
            n += 1
            key = "%s-%d" % (base, n)
        self.taken[key] = label_en
        self.by_label[label_en] = key
        return key

    def near_duplicates(self):
        groups = {}
        for key, label in self.taken.items():
            groups.setdefault(slug_for(label), []).append((key, label))
        return {base: g for base, g in groups.items() if len(g) > 1}


def main():
    pages = {code: lots_of(rel) for code, rel in LANGS}
    counts = {c: len(v) for c, v in pages.items()}
    if len(set(counts.values())) != 1:
        raise SystemExit("pages disagree on how many lots there are: %s" % counts)
    n = counts["en"]

    rows, texts = [], []
    vocab = {}          # key -> {lang: label}
    keys = Keys()

    for i in range(n):
        en = pages["en"][i]
        lot_id = attr(en, "data-lot-id")
        if not lot_id:
            raise SystemExit("lot %d has no data-lot-id" % (i + 1))

        # --- the numbers and tokens, taken from the English page ---
        meta_en = text(en, r'lot-meta">(.*?)</p>')
        meta_en = re.sub(r"<span class=\"lot-est\".*?</span>", "", meta_en, flags=re.S)
        meta_en = re.sub(r"<[^>]+>", "", meta_en).strip()

        km_approx = "1" if meta_en.startswith("~") else "0"
        note_by_lang = {}
        for code in CODES:
            m = text(pages[code][i], r'lot-meta">(.*?)</p>')
            m = re.sub(r"<span class=\"lot-est\".*?</span>", "", m, flags=re.S)
            m = re.sub(r"<[^>]+>", "", m).strip()
            note_by_lang[code] = m.split("·", 1)[1].strip() if "·" in m else ""

        # --- feature tags: vocabulary keys plus the four "N Spaces" strays ---
        feature_keys, spaces = [], ""
        for j, (highlighted, label_en) in enumerate(tags_of(en)):
            hit = SPACES.match(label_en)
            if hit:
                # A count, not a vocabulary item. It becomes a number in its
                # own column, but a placeholder holds its slot so the tags
                # keep the order they sit in today.
                spaces = re.sub(r"[^\d]", "", hit.group(1))
                feature_keys.append("@spaces")
                continue
            key = keys.key(label_en)
            feature_keys.append(("*" if highlighted else "") + key)

            per_lang = vocab.setdefault(key, {})
            for code in CODES:
                other = tags_of(pages[code][i])
                if j >= len(other):
                    raise SystemExit("%s lot %s has fewer tags than en" % (code, lot_id))
                per_lang.setdefault(code, other[j][1])

        rows.append({
            "lot_id": lot_id,
            "name": text(en, r'lot-name">([^<]*)<'),
            "type": attr(en, "data-type"),
            "access": attr(en, "data-access"),
            "km": attr(en, "data-km"),
            "km_approx": km_approx,
            "price_ft": attr(en, "data-amount"),
            "price_unit": attr(en, "data-unit"),
            "price_approx": attr(en, "data-approx"),
            "spaces": spaces,
            "facets": attr(en, "data-features"),
            "features": "|".join(feature_keys),
            "booking_url": text(en, r'<a href="([^"]+)"[^>]*class="card-link"'),
        })

        row = {"lot_id": lot_id}
        for code in CODES:
            block = pages[code][i]
            row["name_" + code] = text(block, r'lot-name">([^<]*)<')
            row["note_" + code] = note_by_lang[code]
            row["description_" + code] = text(block, r'card-description">([^<]*)<')
            row["link_label_" + code] = text(block, r'class="card-link">([^<]*)<')
        texts.append(row)

    dupes = keys.near_duplicates()
    if dupes:
        print("%d concept(s) are written more than one way today. They are kept"
              " apart so this extraction changes nothing; merge them by editing"
              " the features column in data/lots.csv:" % len(dupes))
        for base in sorted(dupes):
            for key, label in sorted(dupes[base]):
                print("  %-18s %s" % (key, label))

    # --- the chrome around each lot, currently hard-coded per page ---
    chrome = {}
    for code, rel in LANGS:
        page = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        one = pages[code][0]
        chrome.setdefault("details", {})[code] = re.search(
            r'aria-label="([^:"]+): ', one).group(1)
        chrome.setdefault("official", {})[code] = re.search(
            r'lot-tag official">([^<]*)<', page).group(1)
        chrome.setdefault("estimate", {})[code] = re.search(
            r'lot-est">([^<]*)<', page).group(1)
        # Every page says "from airport" in English today; this is where that
        # gets fixed, once, instead of in 231 places.
        offsite = next(b for b in pages[code] if 'data-type="offsite"' in b)
        meta = re.sub(r"<[^>]+>", "", re.search(r'lot-meta">(.*?)</p>', offsite, re.S).group(1))
        chrome.setdefault("from_airport", {})[code] = re.sub(
            r"^~?[\d.]+ km\s*", "", meta).split("\u00b7")[0].strip()

        # "1,440 Spaces" / "1.440 hely" / "1 440 miest": the word and the
        # thousands separator both differ, and both were hard-coded per page.
        counted = re.findall(r'feature-tag[^"]*">(\d[\d.,\s\u00a0]*\d)\s+(\S+)</span>', page)
        chrome.setdefault("spaces", {})[code] = counted[0][1]
        grouped = next(n for n, _ in counted if not n.isdigit())
        chrome.setdefault("thousands", {})[code] = next(
            c for c in grouped if not c.isdigit())

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)

    with open(os.path.join(ROOT, "data/ui-labels.csv"), "w", encoding="utf-8", newline="") as fh:
        out = csv.writer(fh, lineterminator="\n")
        out.writerow(["key"] + CODES)
        for key in ("details", "official", "estimate", "from_airport",
                    "spaces", "thousands"):
            out.writerow([key] + [chrome[key][c] for c in CODES])

    with open(os.path.join(ROOT, "data/lots.csv"), "w", encoding="utf-8", newline="") as fh:
        out = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        out.writeheader()
        out.writerows(rows)

    with open(os.path.join(ROOT, "data/lot-text.csv"), "w", encoding="utf-8", newline="") as fh:
        out = csv.DictWriter(fh, fieldnames=list(texts[0]), lineterminator="\n")
        out.writeheader()
        out.writerows(texts)

    with open(os.path.join(ROOT, "data/labels.csv"), "w", encoding="utf-8", newline="") as fh:
        out = csv.writer(fh, lineterminator="\n")
        out.writerow(["feature_key"] + CODES)
        for key in sorted(vocab):
            out.writerow([key] + [vocab[key].get(c, "") for c in CODES])

    print("wrote data/lots.csv (%d lots), data/lot-text.csv, data/labels.csv (%d labels)"
          % (len(rows), len(vocab)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
