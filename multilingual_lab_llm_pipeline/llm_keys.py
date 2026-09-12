"""Central API-key handling for the pipeline.

No key is ever stored in the repository. Keys are read from the process
environment, which can optionally be seeded from a local `.env` file sitting
next to this module (`.env` is git-ignored; copy `.env.example` to start one).

Every stage that talks to a provider resolves its key through `require()`, so a
missing or empty key fails immediately with an actionable message instead of
producing a run full of `__ERROR__` rows.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(HERE, ".env")

# Provider key variables referenced by models.yaml and translate.py.
KNOWN_KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
              "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY")

_loaded = False


def load_dotenv(path=DOTENV_PATH):
    """Seed os.environ from a `KEY=value` file. Variables already set win."""
    global _loaded
    if _loaded or not os.path.exists(path):
        _loaded = True
        return
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if name and not os.environ.get(name):
                os.environ[name] = value
    _loaded = True


def get(env_var, default=""):
    """Return the value of `env_var` (after loading `.env`), or `default`."""
    load_dotenv()
    return os.environ.get(env_var, default).strip()


def require(env_var):
    """Return the value of `env_var`, or exit with an explanation."""
    value = get(env_var)
    if not value:
        raise SystemExit(
            f"{env_var} is not set.\n"
            f"  Either export it:  export {env_var}=...\n"
            f"  or put it in {DOTENV_PATH} (copy .env.example, which is git-ignored).\n"
            f"  Never commit a key; if one has been pasted anywhere public, revoke it first."
        )
    return value


def mask(value):
    """Render a key for logs: first 6 and last 4 characters only."""
    if not value:
        return "(unset)"
    return value[:6] + "…" + value[-4:] if len(value) > 14 else "…" + value[-4:]


def available():
    """Return {env_var: bool} for every key the pipeline knows about."""
    load_dotenv()
    return {name: bool(get(name)) for name in KNOWN_KEYS}
