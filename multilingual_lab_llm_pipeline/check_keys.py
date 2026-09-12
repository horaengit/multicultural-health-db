"""Stage 0 — verify that every model in models.yaml has a usable API key.

Run this before any paid stage. Without `--live` it only reports which keys are
present; with `--live` it sends one tiny request per model (a few tokens, well
under a cent in total) and reports the exact provider error if a key is
rejected, so a wrong or revoked key surfaces here rather than 8,400 calls in.

Usage:  python check_keys.py            # presence only
        python check_keys.py --live     # one real request per configured model
        python check_keys.py --live --only gpt
"""
import argparse, os, sys, yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import llm_keys
from run_models import key_env


def ping(model_cfg):
    """Send the smallest possible request. Returns None on success, else the error text."""
    key = llm_keys.get(key_env(model_cfg))
    try:
        if model_cfg["provider"] == "anthropic":
            import anthropic
            anthropic.Anthropic(api_key=key).messages.create(
                model=model_cfg["model"], max_tokens=1,
                messages=[{"role": "user", "content": "ping"}])
        else:
            from openai import OpenAI
            OpenAI(api_key=key, base_url=model_cfg.get("base_url")).chat.completions.create(
                model=model_cfg["model"], max_tokens=1,
                messages=[{"role": "user", "content": "ping"}])
    except Exception as e:  # provider SDKs raise many distinct types; the message is what matters
        return f"{type(e).__name__}: {e}"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=os.path.join(HERE, "models.yaml"))
    ap.add_argument("--only", nargs="+", default=None, help="check only these model names")
    ap.add_argument("--live", action="store_true", help="send one real request per model")
    args = ap.parse_args()

    models = yaml.safe_load(open(args.models))["models"]
    if args.only:
        models = [m for m in models if m["name"] in args.only]
    if not models:
        raise SystemExit("no models selected")

    failures = 0
    for m in models:
        var = key_env(m)
        key = llm_keys.get(var)
        label = f"{m['name']:<9} {m['model']:<20} {var}={llm_keys.mask(key)}"
        if not key:
            print(f"MISSING  {label}")
            failures += 1
            continue
        if not args.live:
            print(f"present  {label}")
            continue
        err = ping(m)
        if err:
            print(f"FAILED   {label}\n         {err}")
            failures += 1
        else:
            print(f"OK       {label}")

    if failures:
        print(f"\n{failures} of {len(models)} model(s) not usable. "
              f"Set the missing keys in {llm_keys.DOTENV_PATH} or the environment.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
