"""Stage 3 — model runs and automatic scoring.

Design: cases (40 pilot / 200 full) x languages (en ko ar th) x items (closed, open)
        x strategies (direct, translate) x models x repeats (3), temperature 0.

Models are addressed through OpenAI-compatible endpoints so one client covers OpenAI, DeepSeek,
Qwen, Gemini (via OpenAI compatibility) and local vLLM servers; Anthropic uses its own SDK.
Configure in models.yaml. Outputs: runs/outputs.jsonl (raw), runs/closed_scored.csv,
runs/rating_sheet_{lang}.xlsx (25% stratified sample of open answers for native raters).

Usage: python run_models.py --langs en ko --repeats 3 --limit 40
"""
import argparse, json, os, random, re, sys, time, yaml
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_reports import render, L, KO_TERMS
import llm_keys

def load_verified(lang):
    """Return {case_id: {field: verified text}} from the co-author-verified workbook (falls back to draft)."""
    p = os.path.join(HERE, "translations", f"verify_{lang}.xlsx")
    if not os.path.exists(p):
        return {}
    df = pd.read_excel(p).fillna("")
    out = {}
    for r in df.itertuples():
        txt = r.verified_translation or r.draft_translation
        out.setdefault(r.case_id, {})[r.field] = txt
    return out

def localise(case, lang, ver):
    """Apply verified translations of free-text fields to a copy of the case."""
    if lang == "en" or case["case_id"] not in ver:
        return case
    v = ver[case["case_id"]]
    c = json.loads(json.dumps(case))
    c["context"] = v.get("context", c["context"]); c["question"] = v.get("question", c["question"])
    c["options"] = [v.get(f"option_{i}", o) for i, o in enumerate(c["options"])]
    for j, a in enumerate(c["analytes"]):
        a["analyte"] = v.get(f"analyte_{j}", a["analyte"]); a["value"] = v.get(f"value_{j}", a["value"]); a["ref"] = v.get(f"ref_{j}", a["ref"])
    return c

def key_env(model_cfg):
    """Environment variable holding this model's key (explicit, else the provider default)."""
    default = "ANTHROPIC_API_KEY" if model_cfg["provider"] == "anthropic" else "OPENAI_API_KEY"
    return model_cfg.get("key_env", default)

def call(model_cfg, system, user):
    if model_cfg["provider"] == "anthropic":
        import anthropic
        cl = anthropic.Anthropic(api_key=llm_keys.require(key_env(model_cfg)))
        r = cl.messages.create(model=model_cfg["model"], max_tokens=600, temperature=0,
                               system=system, messages=[{"role": "user", "content": user}])
        return r.content[0].text
    from openai import OpenAI
    cl = OpenAI(api_key=llm_keys.require(key_env(model_cfg)), base_url=model_cfg.get("base_url"))
    r = cl.chat.completions.create(model=model_cfg["model"], temperature=0, max_tokens=600,
                                   messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return r.choices[0].message.content

SYSTEM = {"en": "You are a clinical laboratory consultant.", "ko": "당신은 임상검사의학 자문의입니다.",
          "ar": "أنت استشاري في الطب المخبري السريري.", "th": "คุณเป็นแพทย์ที่ปรึกษาด้านเวชศาสตร์ชันสูตร"}

def extract_choice(text):
    m = re.search(r"\b([ABCD])\b", text.strip()[:40])
    return m.group(1) if m else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", nargs="+", default=["en", "ko", "ar", "th"])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--models", default=os.path.join(HERE, "models.yaml"))
    ap.add_argument("--only", nargs="+", default=None,
                    help="run only these model names from models.yaml (e.g. --only gpt)")
    args = ap.parse_args()
    models = yaml.safe_load(open(args.models))["models"]
    if args.only:
        known = {m["name"] for m in models}
        unknown = [n for n in args.only if n not in known]
        if unknown:
            raise SystemExit(f"unknown model name(s) {unknown}; models.yaml defines {sorted(known)}")
        models = [m for m in models if m["name"] in args.only]
    # Fail before spending anything if a key is missing: every selected model needs one.
    for m in models:
        llm_keys.require(key_env(m))
    print("models: " + ", ".join(f"{m['name']}={m['model']}" for m in models))
    cases = [json.loads(l) for l in open(os.path.join(HERE, "cases.jsonl"), encoding="utf-8")][: args.limit]
    os.makedirs(os.path.join(HERE, "runs"), exist_ok=True)
    out_path = os.path.join(HERE, "runs", "outputs.jsonl")
    done = set()
    if os.path.exists(out_path):
        for l in open(out_path, encoding="utf-8"):
            d = json.loads(l); done.add((d["case_id"], d["lang"], d["item"], d["strategy"], d["model"], d["rep"]))
    fout = open(out_path, "a", encoding="utf-8")
    for lang in args.langs:
        ver = load_verified(lang) if lang != "en" else {}
        for c in cases:
            lc = localise(c, lang, ver)
            for item in ("closed", "open"):
                for strat in ("direct", "translate"):
                    if strat == "translate" and lang == "en":
                        continue
                    report, prompt = render(lc, lang if lang in L else "en", item, strat)
                    for m in models:
                        for rep in range(args.repeats):
                            key = (c["case_id"], lang, item, strat, m["name"], rep)
                            if key in done:
                                continue
                            t0 = time.time()
                            try:
                                txt = call(m, SYSTEM[lang], report + "\n\n" + prompt)
                            except Exception as e:
                                txt = f"__ERROR__ {e}"
                            rec = dict(case_id=c["case_id"], lang=lang, item=item, strategy=strat, model=m["name"],
                                       rep=rep, latency_s=round(time.time() - t0, 2), response=txt,
                                       choice=extract_choice(txt) if item == "closed" else None,
                                       correct=(extract_choice(txt) == c["answer"]) if item == "closed" else None)
                            fout.write(json.dumps(rec, ensure_ascii=False) + "\n"); fout.flush()
    fout.close()
    # ---- automatic scoring of closed items
    df = pd.DataFrame([json.loads(l) for l in open(out_path, encoding="utf-8")])
    closed = df[df.item == "closed"]
    closed.to_csv(os.path.join(HERE, "runs", "closed_scored.csv"), index=False)
    print(closed.groupby(["lang", "strategy", "model"]).correct.mean().unstack("model").round(3))
    # ---- rating sheets: 25% stratified sample of open items (by severity x language), rep 0 only
    sev = {c["case_id"]: c["severity"] for c in cases}
    opn = df[(df.item == "open") & (df.rep == 0)].copy()
    opn["severity"] = opn.case_id.map(sev)
    random.seed(2026)
    for lang in args.langs:
        sub = opn[opn.lang == lang]
        ids = []
        for s, g in sub.groupby("severity"):
            cids = sorted(g.case_id.unique()); random.shuffle(cids); ids += cids[: max(1, round(len(cids) * 0.25))]
        sheet = sub[sub.case_id.isin(ids)].sample(frac=1, random_state=2026)  # shuffle to blind model identity
        sheet = sheet.assign(blind_id=range(1, len(sheet) + 1))
        ref = {c["case_id"]: c for c in cases}
        sheet["reference_key_findings"] = sheet.case_id.map(lambda i: ref[i]["key_findings"])
        sheet["reference_interpretation"] = sheet.case_id.map(lambda i: ref[i]["interpretation"])
        sheet["reference_next_step"] = sheet.case_id.map(lambda i: ref[i]["next_step"])
        sheet["must_not"] = sheet.case_id.map(lambda i: ref[i]["must_not"])
        cols = ["blind_id", "case_id", "strategy", "response", "reference_key_findings", "reference_interpretation",
                "reference_next_step", "must_not"]
        rate = sheet[cols].copy()
        for col in ["accuracy_correct_1_0", "hallucination_1_0", "safety_critical_error_1_0",
                    "completeness_1_5", "appropriateness_1_5", "rater_comment"]:
            rate[col] = ""
        rate.to_excel(os.path.join(HERE, "runs", f"rating_sheet_{lang}.xlsx"), index=False)
        sheet[["blind_id", "model", "rep"]].to_csv(os.path.join(HERE, "runs", f"rating_key_{lang}.csv"), index=False)
        print(f"{lang}: rating sheet with {len(rate)} responses (model identity blinded; key saved separately)")

if __name__ == "__main__":
    main()
