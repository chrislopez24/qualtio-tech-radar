from __future__ import annotations


STACKEXCHANGE_TAG_ALIASES = {
    "material-ui": ["material-ui", "mui"],
    "next.js": ["next.js", "nextjs"],
    "node": ["node", "node.js", "nodejs"],
    "three.js": ["three.js", "threejs"],
}

PACKAGE_OVERRIDES = {
    "django": {"deps_dev": "pypi:django", "pypistats": "django"},
    "fastapi": {"deps_dev": "pypi:fastapi", "pypistats": "fastapi"},
    "langchain": {"deps_dev": "pypi:langchain", "pypistats": "langchain"},
    "langflow": {"deps_dev": "pypi:langflow", "pypistats": "langflow"},
    "next.js": {"deps_dev": "npm:next"},
    "open-webui": {"deps_dev": "pypi:open-webui", "pypistats": "open-webui"},
    "pytorch": {"deps_dev": "pypi:torch", "pypistats": "torch"},
    "react": {"deps_dev": "npm:react"},
    "transformers": {"deps_dev": "pypi:transformers", "pypistats": "transformers"},
    "typescript": {"deps_dev": "npm:typescript"},
    "youtube-dl": {"deps_dev": "pypi:youtube-dl", "pypistats": "youtube-dl"},
    "yt-dlp": {"deps_dev": "pypi:yt-dlp", "pypistats": "yt-dlp"},
}


def stackexchange_tags_for(name: str) -> list[str]:
    normalized = _normalize(name)
    return list(STACKEXCHANGE_TAG_ALIASES.get(normalized, [normalized]))


def deps_dev_subject_for(name: str, *, ecosystem: str | None) -> str | None:
    normalized = _normalize(name)
    return PACKAGE_OVERRIDES.get(normalized, {}).get("deps_dev")


def pypistats_subject_for(name: str) -> str | None:
    normalized = _normalize(name)
    return PACKAGE_OVERRIDES.get(normalized, {}).get("pypistats")


def _normalize(value: str) -> str:
    return str(value or "").strip().lower()
