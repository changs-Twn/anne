import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_REQUIRED = ("DB_SERVER", "DB_NAME", "DB_UID", "DB_PWD")


def bootstrap_db_env():
    """Populate os.environ from st.secrets before app.config / app.db are imported.

    app/config.py reads os.environ[...] at import time and is reused unchanged from the
    Flask app; .env (python-dotenv, local dev) already populates os.environ, so st.secrets
    (Streamlit Cloud's Secrets panel) is only consulted for whatever .env didn't provide.
    Must run before any `from app.db import ...` / `from streamlit_pages... import ...`.
    """
    try:
        secrets = st.secrets
    except Exception:
        secrets = {}

    for key in (*_REQUIRED, "SECRET_KEY"):
        if key in os.environ:
            continue
        try:
            if key in secrets:
                os.environ[key] = str(secrets[key])
        except Exception:
            pass

    missing = [k for k in _REQUIRED if k not in os.environ]
    if missing:
        raise RuntimeError(
            "Missing DB config: " + ", ".join(missing) +
            ". Set them in .env (local dev) or Streamlit Cloud's Secrets panel "
            "(see .streamlit/secrets.toml.example)."
        )
