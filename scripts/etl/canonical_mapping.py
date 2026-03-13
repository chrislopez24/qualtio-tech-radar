from __future__ import annotations

PACKAGE_OVERRIDES = {
    "django": {"deps_dev": "pypi:django"},
    "fastapi": {"deps_dev": "pypi:fastapi"},
    "langchain": {"deps_dev": "pypi:langchain"},
    "langflow": {"deps_dev": "pypi:langflow"},
    "next.js": {"deps_dev": "npm:next"},
    "open-webui": {"deps_dev": "pypi:open-webui"},
    "pytorch": {"deps_dev": "pypi:torch"},
    "react": {"deps_dev": "npm:react"},
    "transformers": {"deps_dev": "pypi:transformers"},
    "typescript": {"deps_dev": "npm:typescript"},
    "youtube-dl": {"deps_dev": "pypi:youtube-dl"},
    "yt-dlp": {"deps_dev": "pypi:yt-dlp"},
}


def deps_dev_subject_for(name: str, *, ecosystem: str | None) -> str | None:
    normalized = _normalize(name)
    return PACKAGE_OVERRIDES.get(normalized, {}).get("deps_dev")


def _normalize(value: str) -> str:
    return str(value or "").strip().lower()
