# Multilingual LLM laboratory-interpretation benchmark — pipeline

Stages (run in order; each stage is resumable):

0. `python check_keys.py --live`  — confirms every model in models.yaml has a key the provider accepts (see **API keys** below)
1. `python build_reports.py`  — renders 40 pilot cases (200 in the full study) into EN/KO reports; writes cases.jsonl
2. `python translate.py --langs ko ar th`  — LLM draft translations -> translations/verify_{lang}.xlsx
   Native co-authors fill `verified_translation` (KO: Author 5, AR: Author 2, TH: Author 3). Leave blank to accept draft.
   A language whose workbook already exists is skipped; `--overwrite` redrafts it and carries any verified text across.
3. `python run_models.py --langs en ko ar th --repeats 3`  — all model calls (temperature 0), auto-scores closed items,
   builds blinded rating sheets runs/rating_sheet_{lang}.xlsx (25% stratified sample of open answers)
4. `Rscript analysis.R`  — pre-specified mixed-effects analysis, language-gap contrasts, consistency kappa

## API keys

Keys are read from the environment, optionally seeded from a local `.env` file in this directory.
`.env` is git-ignored and must never be committed.

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in the keys you actually use
python check_keys.py --live # one tiny request per model; confirms each key is accepted
```

`check_keys.py` is stage 0: run it before any paid stage, so a wrong, revoked, or
quota-exhausted key surfaces immediately instead of after thousands of calls.
Exporting the variables in the shell works just as well as `.env`; anything already set in the
environment takes precedence over the file.

Variables, as referenced by `models.yaml`: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, `DASHSCOPE_API_KEY`. A model entry may name a different
variable with `key_env:`. `OPENAI_BASE_URL` (or `--base-url`) points `translate.py` at any
OpenAI-compatible endpoint.

Only the models you actually select need a key: `python run_models.py --only gpt` runs the
OpenAI model alone, and every selected model's key is validated before the first request is sent.

If a key is ever exposed — pasted into a chat, a ticket, or a commit — revoke it at the provider
and issue a new one. Rotating is cheap; a leaked key is not.

## Cost

Estimated cost for the pilot (40 cases x 4 langs x 2 items x ~1.75 strategies x 5 models x 3 reps ≈ 8,400 calls): roughly USD 30–60.
Full study (200 cases) ≈ 42,000 calls: roughly USD 150–300 depending on models.
Freeze `run_date` and model identifiers in models.yaml before the full run and report them verbatim.
