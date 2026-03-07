from __future__ import annotations

from typing import Any, Callable


ACTUAL_LANGUAGE_NAMES = {
    "c#",
    "csharp",
    "go",
    "golang",
    "java",
    "javascript",
    "kotlin",
    "php",
    "python",
    "ruby",
    "rust",
    "swift",
    "typescript",
}

LANGUAGE_IDS = {
    "python",
    "javascript",
    "typescript",
    "rust",
    "go",
    "java",
    "c#",
    "kotlin",
    "swift",
    "php",
    "ruby",
}

PLATFORM_KEYWORDS = [
    "kubernetes", "docker", "cloud", "platform", "infra", "infrastructure",
    "devops", "terraform", "ansible", "aws", "gcp", "azure", "linux", "hosting",
    "deployment", "orchestration", "runtime", "backend", "service", "serverless",
    "database", "queue", "stream", "broker", "gateway", "workflow", "monitoring",
]

TECHNIQUE_KEYWORDS = [
    "guide", "roadmap", "tutorial", "book", "books", "course", "interview",
    "awesome", "algorithms", "patterns", "architecture", "best practices", "learning",
]

TOOL_KEYWORDS = [
    "tool", "cli", "command-line", "editor", "plugin", "extension", "sdk", "framework",
    "library", "interface", "shell", "webui",
]


def _normalized_tokens(value: str) -> set[str]:
    return {token for token in "".join(ch if ch.isalnum() else " " for ch in value.lower()).split() if token}


def _normalized_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


NORMALIZED_LANGUAGE_NAMES = {_normalized_name(value) for value in ACTUAL_LANGUAGE_NAMES}


def _has_tool_topic(topics: list[str]) -> bool:
    exact_tokens = {"testing", "tool", "framework", "library", "ui", "cli"}
    prefix_tokens = {"tool"}

    for topic in topics:
        tokens = _normalized_tokens(topic)
        if tokens & exact_tokens:
            return True
        if any(token.startswith(prefix) for token in tokens for prefix in prefix_tokens):
            return True

    return False


def _is_actual_language(name: str, lang: str, topics: list[str], text: str) -> bool:
    del lang, topics, text

    if _normalized_name(name) in NORMALIZED_LANGUAGE_NAMES:
        return True

    return False


def infer_quadrant(tech: Any) -> str:
    """Infer quadrant from technology characteristics."""
    name = getattr(tech, "name", "") or ""
    lang = (getattr(tech, "language", "") or "").lower()
    topics = [str(t).lower() for t in getattr(tech, "topics", [])]
    text = f"{name} {getattr(tech, 'description', '')}".lower()

    if any(keyword in text for keyword in PLATFORM_KEYWORDS) or any(
        t in topics for t in ["devops", "cloud", "infrastructure", "kubernetes", "platform"]
    ):
        return "platforms"

    if any(t in topics for t in ["testing", "tool", "framework", "library"]) or _has_tool_topic(topics) or any(
        keyword in text for keyword in TOOL_KEYWORDS
    ):
        return "tools"

    if any(keyword in text for keyword in TECHNIQUE_KEYWORDS):
        return "techniques"

    if _is_actual_language(name, lang, topics, text):
        return "languages"

    return "techniques"


def quadrant_affinity(tech: Any, target_quadrant: str, infer_domain: Callable[[Any], str]) -> float:
    """Score how naturally a technology fits a target quadrant."""
    lang = (getattr(tech, "language", "") or "").lower()
    topics = [str(t).lower() for t in getattr(tech, "topics", [])]
    text = f"{getattr(tech, 'name', '')} {getattr(tech, 'description', '')}".lower()
    domain = (getattr(tech, "domain", None) or infer_domain(tech)).lower()

    score = 0.0

    if target_quadrant == "platforms":
        platform_keywords = PLATFORM_KEYWORDS + ["observability", "server"]
        score += sum(1.0 for keyword in platform_keywords if keyword in text)
        score += sum(1.5 for topic in ["devops", "cloud", "infrastructure", "kubernetes", "platform"] if topic in topics)
        if domain in {"devops", "backend", "systems"}:
            score += 1.5

    elif target_quadrant == "tools":
        tool_keywords = TOOL_KEYWORDS + ["automation"]
        score += sum(1.0 for keyword in tool_keywords if keyword in text)
        score += sum(1.5 for topic in ["testing", "tool", "framework", "library"] if topic in topics)
        if domain in {"frontend", "backend"}:
            score += 0.5

    elif target_quadrant == "languages":
        if _is_actual_language(getattr(tech, "name", "") or "", lang, topics, text):
            score += 3.0
        score += sum(1.0 for keyword in ["language", "compiler", "runtime", "interpreter"] if keyword in text)
        if domain in {"systems", "data science"}:
            score += 0.5

    elif target_quadrant == "techniques":
        score += sum(1.0 for keyword in TECHNIQUE_KEYWORDS if keyword in text)
        if domain == "general":
            score += 0.5

    return score
