"""Stage 2b — triage the draft translations before the native co-authors review them.

The co-author, not this script, decides what the final text says. All this does is
narrow down where they have to look, which matters because `verify_{lang}.xlsx` holds
1,218 rows per language while carrying only a few hundred distinct strings.

Two things cut that down:

* Deduplication. "Negative" appears 213 times in the Korean workbook. The co-author
  should rule on it once, so the review sheet carries one row per distinct
  (english, draft) pair and `--apply` fans the decision back out to every occurrence.
* Back-translation. Each distinct draft is translated back into English and compared
  with the source, which surfaces drafts that changed the meaning. Mechanical checks
  run alongside it for dropped abbreviations, dropped numbers, and untranslated text.

Back-translation is a triage signal, never a verdict: an unflagged row is one no
automated check objected to, not one that has been verified. Only a co-author's entry
in `verified_translation` counts as verification, and note that the back-translator is
currently the same model that produced the drafts, so it is the weakest of the checks
here. Point it at a different model with --model once another provider key is in place.

Usage:  python qc_translations.py --langs ko ar th     # build translations/qc_{lang}.xlsx
        python qc_translations.py --langs ko --apply   # merge decisions into verify_ko.xlsx
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
import llm_keys

HERE = os.path.dirname(os.path.abspath(__file__))
LANG_NAME = {"ko": "Korean", "ar": "Modern Standard Arabic", "th": "Thai"}

# Ranges wide enough to tell "the co-author will see their own script" from
# "the draft came back in the wrong alphabet"; they are not a spell check.
SCRIPTS = {
    "ko": [(0xAC00, 0xD7A3), (0x1100, 0x11FF), (0x3130, 0x318F)],
    "ar": [(0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF)],
    "th": [(0x0E00, 0x0E7F)],
}

# Spelled out in translate.py's system prompt, so a draft that drops one has ignored
# an explicit instruction. Longest first, so CFU/mL is matched before CFU.
PROTECTED = ("CFU/mL", "ng/mL", "mmHg", "HPF", "PSA", "PCR", "HPV", "DNA", "RNA")

# Ordinary English words that happen to be capitalised for emphasis. Without these,
# "rifampicin resistance NOT detected" reads as an abbreviation the draft dropped.
NOT_ABBREVIATIONS = {"NOT", "AND", "OR", "NO", "IF", "ALL", "ANY", "THE", "NONE", "NEW"}

BACK_SYS = ("Translate each {lang} medical string back into English. Translate literally, "
            "preserving the wording rather than improving it, so the result can be compared "
            "with the original. Return ONLY a JSON object with the same keys.")

PROSE = re.compile(r"context|question|option_")
NUM = re.compile(r"\d+(?:\.\d+)?")
ABBR = re.compile(r"\b[A-Z]{2,}\d*\b")
WORD = re.compile(r"[a-z0-9]+")


def has_script(text, lang):
    return any(any(lo <= ord(ch) <= hi for lo, hi in SCRIPTS[lang]) for ch in str(text))


def protected_terms(english):
    """Terms translate.py was told to leave alone, as they appear in this string.

    Matching is bounded on both sides, because a plain substring test finds "RNA"
    inside "hypernatraemia" and "alternative" and reports a loss that never happened.
    """
    found, rest = [], str(english)
    for term in PROTECTED:
        bounded = r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])"
        if re.search(bounded, rest, flags=re.I):
            found.append(term)
            rest = re.sub(bounded, " ", rest, flags=re.I)
    return found + [t for t in ABBR.findall(rest)
                    if t not in found and t.upper() not in NOT_ABBREVIATIONS]


def numbers_lost(english, draft):
    """Numbers present in the source but missing from the draft.

    A draft may legitimately add numbers -- "two weeks" becomes "2주" -- so this
    only looks for losses, counting repeats so 158/98 cannot be satisfied by one 98.
    """
    remaining = NUM.findall(str(draft))
    lost = []
    for n in NUM.findall(str(english)):
        if n in remaining:
            remaining.remove(n)
        else:
            lost.append(n)
    return lost


def drift(english, backtranslation):
    """Word overlap between the source and its back-translation, 0.0 to 1.0.

    Deliberately crude. It ranks rows for human attention; it does not score a
    translation, and a low value is a prompt to look rather than a defect.
    """
    a = set(WORD.findall(str(english).lower()))
    b = set(WORD.findall(str(backtranslation).lower()))
    if not a or not b:
        return 1.0
    return len(a & b) / len(a | b)


def check(english, draft, field, lang):
    """Mechanical checks for one (english, draft) pair -> list of flag names."""
    flags = []
    if not str(draft).strip():
        return ["MISSING"]
    if any(ch.isalpha() for ch in str(english)) and str(draft).strip() == str(english).strip():
        flags.append("UNTRANSLATED")
    elif PROSE.match(str(field)) and not has_script(draft, lang):
        flags.append("WRONG_SCRIPT")
    dropped = [t for t in protected_terms(english)
               if not re.search(r"(?<![A-Za-z])" + re.escape(t) + r"(?![A-Za-z])",
                                str(draft), flags=re.I)]
    if dropped:
        flags.append("ABBR_LOST:" + ",".join(dropped))
    lost = numbers_lost(english, draft)
    if lost:
        flags.append("NUM_LOST:" + ",".join(lost))
    return flags


def back_translate(client, model, lang, strings, batch=25):
    """Back-translate distinct strings, batched to keep the request count low."""
    out = {}
    todo = [s for s in strings if s.strip()]
    for start in range(0, len(todo), batch):
        chunk = todo[start:start + batch]
        payload = {str(i): s for i, s in enumerate(chunk)}
        r = client.chat.completions.create(
            model=model, temperature=0,
            messages=[{"role": "system", "content": BACK_SYS.format(lang=LANG_NAME[lang])},
                      {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            response_format={"type": "json_object"})
        got = json.loads(r.choices[0].message.content)
        for i, s in enumerate(chunk):
            out[s] = str(got.get(str(i), ""))
        print(f"  back-translated {min(start + batch, len(todo))}/{len(todo)}")
    return out


def build(lang, client, model):
    src = os.path.join(HERE, "translations", f"verify_{lang}.xlsx")
    if not os.path.exists(src):
        print(f"{lang}: {src} not found -- run translate.py first")
        return
    df = pd.read_excel(src).fillna("")
    df["english"] = df["english"].astype(str)
    df["draft_translation"] = df["draft_translation"].astype(str)

    # One row per distinct pair. The co-author rules once; --apply fans it back out.
    groups = []
    for (english, draft), g in df[df.english.str.strip() != ""].groupby(
            ["english", "draft_translation"], sort=False):
        first = g.iloc[0]
        groups.append({"english": english, "draft_translation": draft,
                       "occurrences": len(g), "field": first["field"],
                       "example_case_id": first["case_id"],
                       "verified_translation": "", "verifier_comment": ""})

    # Identical numeric strings ("1.005-1.030") are correct untranslated, so spending
    # a back-translation on them would only add noise.
    needs_bt = [g["draft_translation"] for g in groups
                if not (g["draft_translation"].strip() == g["english"].strip()
                        and not any(c.isalpha() for c in g["english"]))]
    print(f"{lang}: {len(df)} rows -> {len(groups)} distinct strings, "
          f"{len(set(needs_bt))} to back-translate")
    bt = back_translate(client, model, lang, sorted(set(needs_bt)))

    for g in groups:
        g["backtranslation"] = bt.get(g["draft_translation"], "")
        flags = check(g["english"], g["draft_translation"], g["field"], lang)
        overlap = drift(g["english"], g["backtranslation"]) if g["backtranslation"] else 1.0
        if overlap < 0.4 and not flags:
            flags.append("MEANING_DRIFT")
        g["overlap"] = round(overlap, 2)
        g["flags"] = "; ".join(flags)
        hard = [f for f in flags if not f.startswith("MEANING_DRIFT")]
        g["priority"] = "HIGH" if hard else ("REVIEW" if flags else "OK")

    cols = ["priority", "flags", "occurrences", "field", "example_case_id",
            "english", "draft_translation", "backtranslation", "overlap",
            "verified_translation", "verifier_comment"]
    out = pd.DataFrame(groups)[cols]
    rank = {"HIGH": 0, "REVIEW": 1, "OK": 2}
    out = out.sort_values(["priority", "occurrences"],
                          key=lambda s: s.map(rank) if s.name == "priority" else -s,
                          kind="stable")

    path = os.path.join(HERE, "translations", f"qc_{lang}.xlsx")
    out.to_excel(path, index=False)
    style(path, out)
    counts = out.priority.value_counts()
    print(f"{lang}: HIGH={counts.get('HIGH', 0)}  REVIEW={counts.get('REVIEW', 0)}  "
          f"OK={counts.get('OK', 0)}  -> {path}")


def style(path, df):
    """Freeze the header, widen the text columns, and tint the rows that need attention."""
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    tint = {"HIGH": PatternFill("solid", fgColor="FFC7CE"),
            "REVIEW": PatternFill("solid", fgColor="FFEB9C")}
    wb = load_workbook(path)
    ws = wb.active
    ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for width, col in zip((10, 26, 12, 12, 14, 52, 52, 52, 9, 40, 30), ws.iter_cols(min_row=1)):
        ws.column_dimensions[col[0].column_letter].width = width
    for row in ws.iter_rows(min_row=2):
        fill = tint.get(row[0].value)
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if fill:
                cell.fill = fill
    wb.save(path)


def apply(lang):
    """Copy the co-author's decisions from qc_{lang}.xlsx into every matching row."""
    qc_path = os.path.join(HERE, "translations", f"qc_{lang}.xlsx")
    src = os.path.join(HERE, "translations", f"verify_{lang}.xlsx")
    if not os.path.exists(qc_path):
        print(f"{lang}: {qc_path} not found -- build it first")
        return
    qc = pd.read_excel(qc_path).fillna("")
    decided = {(str(r.english), str(r.draft_translation)):
               (str(r.verified_translation).strip(), str(r.verifier_comment).strip())
               for r in qc.itertuples() if str(r.verified_translation).strip()}
    if not decided:
        print(f"{lang}: no verified text in {qc_path} yet -- nothing to apply")
        return

    df = pd.read_excel(src).fillna("")
    filled = 0
    for i, r in df.iterrows():
        # Text the co-author already entered in verify_{lang}.xlsx wins; this only fills blanks.
        if str(r["verified_translation"]).strip():
            continue
        hit = decided.get((str(r["english"]), str(r["draft_translation"])))
        if hit:
            df.at[i, "verified_translation"] = hit[0]
            if hit[1]:
                df.at[i, "verifier_comment"] = hit[1]
            filled += 1
    df.to_excel(src, index=False)
    print(f"{lang}: {len(decided)} decision(s) -> {filled} row(s) updated in {src}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="+", default=["ko", "ar", "th"])
    ap.add_argument("--model", default="gpt-4o", help="model used for back-translation")
    ap.add_argument("--key-env", default="OPENAI_API_KEY")
    ap.add_argument("--base-url", default=llm_keys.get("OPENAI_BASE_URL") or None)
    ap.add_argument("--apply", action="store_true",
                    help="merge decisions from qc_{lang}.xlsx back into verify_{lang}.xlsx")
    args = ap.parse_args()

    if args.apply:
        for lang in args.langs:
            apply(lang)
        return

    from openai import OpenAI
    client = OpenAI(api_key=llm_keys.require(args.key_env), base_url=args.base_url)
    for lang in args.langs:
        build(lang, client, args.model)


if __name__ == "__main__":
    main()
