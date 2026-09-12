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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="+", default=["ko", "ar", "th"])
    ap.add_argument("--build", action="store_true", help="propose entries from the drafts")
    ap.add_argument("--report", action="store_true", help="show what the glossary would change")
    args = ap.parse_args()
    if args.build:
        build(args.langs)
    elif args.report:
        report(args.langs)
    else:
        ap.error("pass --build or --report")


if __name__ == "__main__":
    main()
