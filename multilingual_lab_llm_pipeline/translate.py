"""Stage 2 — translation.
Drafts KO/AR/TH versions of every free-text field (context, question, options, analyte names/values
not covered by fixed term tables) with one LLM, then writes a verification workbook per language
for the native-speaking co-author (Authors 5, 2, 3). Verified text is read back by run_models.py.

Each case is drafted in its own request, so a value that appears in several cases used to
come back differently in each: "Negative" arrived in the Thai drafts as ลบ 183 times and
as "Negative" 29 times. translations/glossary.yaml fixes those repeated lab values, and
every request carries the entries for its case and has them enforced on the reply. See
glossary.py, and run `python glossary.py --build` after adding cases.

Usage:  python translate.py --model gpt-4o --langs ko ar th
Env:    OPENAI_API_KEY (any OpenAI-compatible endpoint via OPENAI_BASE_URL).
        Set it in the shell or in a local .env file; see llm_keys.py and .env.example.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openai import OpenAI
import pandas as pd
import glossary
import llm_keys

LANG_NAME = {"ko": "Korean", "ar": "Modern Standard Arabic", "th": "Thai"}
SYS = ("You are a certified medical translator. Translate the JSON values into {lang} for clinicians. "
       "Keep numbers, units, gene names, drug names, and abbreviations (PSA, PCR, HPV, CFU/mL, HPF) unchanged. "
       "Return ONLY a JSON object with the same keys.")

def fields(case):
    f = {"context": case["context"], "question": case["question"]}
    for i, o in enumerate(case["options"]):
        f[f"option_{i}"] = o
    for j, a in enumerate(case["analytes"]):
        f[f"analyte_{j}"] = a["analyte"]; f[f"value_{j}"] = a["value"]; f[f"ref_{j}"] = a["ref"]
    return f

def existing_verifications(path):
    """Return {(case_id, field): (verified_translation, verifier_comment)} already filled in a workbook.

    Redrafting must never silently discard a co-author's verified text, so anything a
    verifier has typed is carried into the new workbook.
    """
    if not os.path.exists(path):
        return {}
    df = pd.read_excel(path).fillna("")
    return {(r.case_id, r.field): (str(r.verified_translation), str(r.verifier_comment))
            for r in df.itertuples()}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-4o")
    ap.add_argument("--langs", nargs="+", default=["ko", "ar", "th"])
    ap.add_argument("--key-env", default="OPENAI_API_KEY",
                    help="environment variable holding the key (default OPENAI_API_KEY)")
    ap.add_argument("--base-url", default=llm_keys.get("OPENAI_BASE_URL") or None,
                    help="OpenAI-compatible endpoint (default OPENAI_BASE_URL, else api.openai.com)")
    ap.add_argument("--limit", type=int, default=None, help="translate only the first N cases (smoke test)")
    ap.add_argument("--overwrite", action="store_true",
                    help="redraft a language whose workbook already exists (verified columns are carried over)")
    args = ap.parse_args()
    client = OpenAI(api_key=llm_keys.require(args.key_env), base_url=args.base_url)
    gloss = glossary.load()
    print(f"translating with {args.model} using {args.key_env}={llm_keys.mask(llm_keys.get(args.key_env))}")
    here = os.path.dirname(os.path.abspath(__file__))
    cases = [json.loads(l) for l in open(os.path.join(here, "cases.jsonl"), encoding="utf-8")][: args.limit]
    os.makedirs(os.path.join(here, "translations"), exist_ok=True)
    for lang in args.langs:
        path = os.path.join(here, "translations", f"verify_{lang}.xlsx")
        kept = existing_verifications(path)
        if kept and not args.overwrite:
            print(f"{lang}: {path} already exists — skipping (pass --overwrite to redraft; "
                  f"verified text is carried over)")
            continue
        rows, forced = [], 0
        for c in cases:
            src = fields(c)
            system = SYS.format(lang=LANG_NAME[lang])
            block = glossary.prompt_block(src, lang, gloss)
            if block:
                system += "\n\n" + block
            r = client.chat.completions.create(
                model=args.model, temperature=0,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": json.dumps(src, ensure_ascii=False)}],
                response_format={"type": "json_object"})
            tr = json.loads(r.choices[0].message.content)
            # Each case is its own request, so nothing but this stops a repeated value
            # from coming back one way here and another way in the next case.
            forced += len(glossary.apply(tr, src, lang, gloss))
            for k, v in src.items():
                prev = kept.get((c["case_id"], k), ("", ""))
                rows.append({"case_id": c["case_id"], "field": k, "english": v,
                             "draft_translation": tr.get(k, ""),
                             "verified_translation": prev[0], "verifier_comment": prev[1]})
        pd.DataFrame(rows).to_excel(path, index=False)
        note = f", {forced} field(s) set from the glossary" if forced else ""
        print(f"{lang}: {len(rows)} strings{note} -> {path}  (native co-author fills 'verified_translation')")

if __name__ == "__main__":
    main()
