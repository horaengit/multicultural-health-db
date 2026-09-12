"""Canonical renderings for the lab values that repeat across cases.

translate.py drafts one case per request, so nothing ties the requests together and a
term can come back differently each time. In the Thai drafts "Negative" arrives as ลบ
183 times and as "Negative" 29 times, which means a model reading the Thai condition
meets an English value in some cases and a Thai one in others. The language the study
manipulates is then not the language the cases actually carry.

A glossary fixes each repeated value once. translate.py puts the entries for a case in
its prompt and then enforces them on the reply, so consistency does not depend on the
model choosing to comply.

Only whole-field matches are replaced, and only in the analyte, value, and reference
columns. Prose is left alone: a term inside a sentence has to inflect with it, and in
Arabic and Thai a spliced-in dictionary form would read as a mistake.

For Korean the glossary is seeded from KO_TERMS in build_reports.py, which the team has
already curated and which render() applies anyway -- seeding from it makes the workbook
show the text that will actually reach the model. Arabic and Thai have no such list, so
`--build` proposes the most common rendering already in the drafts and the native
co-author confirms or replaces it. That review is the point: about forty terms per
language, decided once, in place of the same judgement repeated across 1,218 rows.

Usage:  python glossary.py --build            # propose translations/glossary.yaml
        python glossary.py --report           # show what the current file would change
        python glossary.py --sheet --langs ar th   # workbook of what still needs deciding
        python glossary.py --confirm --langs ar th # read those workbooks back in
"""
import argparse, collections, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "translations", "glossary.yaml")
LAB_FIELD = re.compile(r"analyte_|value_|ref_")

HEADER = """\
# Canonical rendering for every lab value that appears in more than one case.
#
# Regenerate the proposals with `python glossary.py --build`; it never overwrites an
# entry that is already here, so edits survive. Korean is seeded from KO_TERMS in
# build_reports.py. Arabic and Thai start from the most common rendering in the current
# drafts and need a native co-author to confirm each one.
#
# Entries under `review:` are proposals nobody has confirmed yet. Move a term up into
# its language block once it has been checked.
"""


def load(path=PATH):
    """Return {lang: {english: canonical}}, empty if the file does not exist yet."""
    if not os.path.exists(path):
        return {}
    data = yaml.safe_load(open(path, encoding="utf-8")) or {}
    out = {}
    for lang, terms in data.items():
        if lang == "review":
            continue
        out[lang] = {str(k): str(v) for k, v in (terms or {}).items()}
    return out


def apply(translated, source, lang, gloss):
    """Overwrite lab fields whose English source has a canonical rendering.

    `translated` is the model's reply keyed by field name and `source` the English it
    was given. Returns the fields that were changed, so callers can report them.
    """
    terms = gloss.get(lang, {})
    if not terms:
        return {}
    changed = {}
    for field, english in source.items():
        if not LAB_FIELD.match(field):
            continue
        canonical = terms.get(str(english).strip())
        if canonical and str(translated.get(field, "")).strip() != canonical:
            changed[field] = (translated.get(field, ""), canonical)
            translated[field] = canonical
    return changed


def prompt_block(source, lang, gloss):
    """The glossary lines for one case, or "" when none of its values are covered."""
    terms = gloss.get(lang, {})
    used = {}
    for field, english in source.items():
        if LAB_FIELD.match(field) and str(english).strip() in terms:
            used[str(english).strip()] = terms[str(english).strip()]
    if not used:
        return ""
    lines = "\n".join(f"{en} = {tr}" for en, tr in sorted(used.items()))
    return ("Use these exact renderings wherever the value appears, so that every case "
            "presents the same term identically:\n" + lines)


def build(langs, path=PATH):
    """Propose a glossary from the drafted workbooks, keeping any existing entries."""
    try:
        from build_reports import KO_TERMS
    except ImportError:
        KO_TERMS = {}

    existing = load(path)
    confirmed = {lang: dict(existing.get(lang, {})) for lang in langs}
    review = {}

    for lang in langs:
        src = os.path.join(HERE, "translations", f"verify_{lang}.xlsx")
        if not os.path.exists(src):
            print(f"{lang}: {src} not found -- skipping")
            continue
        df = pd.read_excel(src).fillna("")
        df = df[df.field.astype(str).str.match(LAB_FIELD)]
        df = df[df.english.astype(str).str.strip() != ""]

        renderings = collections.defaultdict(collections.Counter)
        for r in df.itertuples():
            renderings[str(r.english).strip()][str(r.draft_translation).strip()] += 1

        proposals = {}
        for english, counts in renderings.items():
            if english in confirmed[lang]:
                continue
            # KO_TERMS is already curated and render() applies it whatever the draft
            # says, so pin every term in it. The threshold below exists to keep
            # one-off strings out of the proposals guessed from the drafts, and a
            # term that has already been decided is not a guess.
            if lang == "ko" and english in KO_TERMS:
                confirmed[lang][english] = KO_TERMS[english]
                continue
            if sum(counts.values()) < 2:
                continue
            # A reference range like "0.2-1.0" carries no words to translate. Where
            # every draft already left one alone, there is no decision to put to a
            # co-author, so pin it rather than spend a row of their attention on it.
            if (len(counts) == 1 and english in counts
                    and not any(ch.isalpha() for ch in english)):
                confirmed[lang][english] = english
                continue
            # Leaving the English untouched is the thing being corrected, so it only
            # wins when nothing else was ever produced for this term.
            translated = {k: n for k, n in counts.items() if k and k != english}
            pool = translated or counts
            proposals[english] = max(pool.items(), key=lambda kv: (kv[1], kv[0]))[0]

        if proposals:
            review[lang] = dict(sorted(proposals.items()))
        print(f"{lang}: {len(confirmed[lang])} confirmed, {len(proposals)} awaiting review")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = {lang: dict(sorted(terms.items())) for lang, terms in confirmed.items() if terms}
    if review:
        body["review"] = review
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(HEADER)
        yaml.safe_dump(body, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"wrote {path}")


def report(langs, path=PATH):
    """Show which drafted rows the current glossary would change, without writing."""
    gloss = load(path)
    if not gloss:
        print(f"{path} not found -- run --build first")
        return
    for lang in langs:
        src = os.path.join(HERE, "translations", f"verify_{lang}.xlsx")
        if not os.path.exists(src):
            continue
        df = pd.read_excel(src).fillna("")
        df = df[df.field.astype(str).str.match(LAB_FIELD)]
        terms = gloss.get(lang, {})
        hits = collections.Counter()
        for r in df.itertuples():
            canonical = terms.get(str(r.english).strip())
            if canonical and str(r.draft_translation).strip() != canonical:
                hits[(str(r.english).strip(), str(r.draft_translation).strip(), canonical)] += 1
        total = sum(hits.values())
        print(f"=== {lang.upper()} === {len(terms)} terms, {total} row(s) would change")
        for (english, was, now), n in hits.most_common(10):
            print(f"   {english:<24} {was!r} -> {now!r}  (x{n})")
        print()


def sheet(langs, path=PATH):
    """Write the unconfirmed proposals as one workbook per language for the co-author.

    A term the co-author accepts needs no typing: `decision` is pre-filled with the
    proposal, and they overwrite it only where it is wrong. Every rendering the drafts
    produced is listed beside it, since the disagreement is usually the useful part.
    """
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    data = yaml.safe_load(open(path, encoding="utf-8")) or {}
    review = data.get("review") or {}
    for lang in langs:
        proposals = review.get(lang) or {}
        if not proposals:
            print(f"{lang}: nothing awaiting review")
            continue
        src = os.path.join(HERE, "translations", f"verify_{lang}.xlsx")
        df = pd.read_excel(src).fillna("")
        df = df[df.field.astype(str).str.match(LAB_FIELD)]
        seen = collections.defaultdict(collections.Counter)
        for r in df.itertuples():
            seen[str(r.english).strip()][str(r.draft_translation).strip()] += 1

        rows = []
        for english, proposed in sorted(proposals.items()):
            counts = seen.get(english, collections.Counter())
            rows.append({
                "english": english,
                "decision": proposed,
                "proposed": proposed,
                "occurrences": sum(counts.values()),
                "renderings_in_drafts": " | ".join(f"{k} (x{n})" for k, n in counts.most_common()),
                "disagreed": len(counts) > 1,
                "left_in_english": counts.get(english, 0),
                "comment": "",
            })
        out = os.path.join(HERE, "translations", f"glossary_review_{lang}.xlsx")
        pd.DataFrame(rows).to_excel(out, index=False)

        wb = load_workbook(out)
        ws = wb.active
        ws.freeze_panes = "A2"
        for cell in ws[1]:
            cell.font = Font(bold=True)
        for width, col in zip((30, 30, 30, 12, 46, 11, 14, 30), ws.iter_cols(min_row=1)):
            ws.column_dimensions[col[0].column_letter].width = width
        # Where the drafts disagreed, the proposal is a majority vote over genuinely
        # different answers, so it is the one most worth a second look.
        flag = PatternFill("solid", fgColor="FFC7CE")
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
            if row[5].value:
                for cell in row:
                    cell.fill = flag
        wb.save(out)
        split = sum(1 for r in rows if r["disagreed"])
        print(f"{lang}: {len(rows)} term(s) to confirm ({split} where the drafts "
              f"disagreed) -> {out}")


def confirm(langs, path=PATH):
    """Move decided terms out of `review:` and into the language block."""
    data = yaml.safe_load(open(path, encoding="utf-8")) or {}
    review = data.get("review") or {}
    moved_total = 0
    for lang in langs:
        out = os.path.join(HERE, "translations", f"glossary_review_{lang}.xlsx")
        if not os.path.exists(out):
            print(f"{lang}: {out} not found -- run --sheet first")
            continue
        df = pd.read_excel(out).fillna("")
        moved = {}
        for r in df.itertuples():
            decision = str(r.decision).strip()
            # A cleared cell means "not decided yet", not "render this as nothing".
            if decision:
                moved[str(r.english).strip()] = decision
        if not moved:
            print(f"{lang}: no decisions filled in -- nothing to confirm")
            continue
        data.setdefault(lang, {})
        data[lang].update(moved)
        data[lang] = dict(sorted(data[lang].items()))
        for english in moved:
            (review.get(lang) or {}).pop(english, None)
        if not review.get(lang):
            review.pop(lang, None)
        moved_total += len(moved)
        print(f"{lang}: {len(moved)} term(s) confirmed")

    if not moved_total:
        return
    if review:
        data["review"] = review
    else:
        data.pop("review", None)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(HEADER)
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"wrote {path} -- redraft with `python translate.py --langs ... --overwrite`")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="+", default=["ko", "ar", "th"])
    ap.add_argument("--build", action="store_true", help="propose entries from the drafts")
    ap.add_argument("--report", action="store_true", help="show what the glossary would change")
    ap.add_argument("--sheet", action="store_true",
                    help="write the proposals awaiting review to a workbook per language")
    ap.add_argument("--confirm", action="store_true",
                    help="read those workbooks back and promote the decided terms")
    args = ap.parse_args()
    if args.build:
        build(args.langs)
    elif args.report:
        report(args.langs)
    elif args.sheet:
        sheet(args.langs)
    elif args.confirm:
        confirm(args.langs)
    else:
        ap.error("pass --build, --report, --sheet, or --confirm")


if __name__ == "__main__":
    main()
