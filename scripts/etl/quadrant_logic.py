from __future__ import annotations

from typing import Any, Callable


def infer_quadrant(tech: Any) -> str:
    """Infer quadrant from technology characteristics."""
    lang = (getattr(tech, "language", "") or "").lower()
    topics = [str(t).lower() for t in getattr(tech, "topics", [])]
    text = f"{getattr(tech, 'name', '')} {getattr(tech, 'description', '')}".lower()

    platform_keywords = [
        "kubernetes", "docker", "cloud", "platform", "infra", "infrastructure",
        "devops", "terraform", "ansible", "aws", "gcp", "azure", "linux", "hosting",
        "deployment", "orchestration", "runtime", "backend", "service", "serverless",
        "database", "queue", "stream", "broker", "gateway", "workflow", "monitoring",
    ]
    if any(keyword in text for keyword in platform_keywords) or any(
        t in topics for t in ["devops", "cloud", "infrastructure", "kubernetes", "platform"]
    ):
        return "platforms"

    technique_keywords = [
        "guide", "roadmap", "tutorial", "book", "books", "course", "interview",
        "awesome", "algorithms", "patterns", "architecture", "best practices", "learning",
    ]
    if any(keyword in text for keyword in technique_keywords):
        return "techniques"

    if any(t in topics for t in ["testing", "tool", "framework", "library"]) or any(
        keyword in text for keyword in ["tool", "cli", "editor", "plugin", "extension", "sdk", "framework", "library"]
    ):
        return "tools"

    if lang in ["python", "javascript", "typescript", "rust", "go", "java", "c#", "kotlin", "swift", "php", "ruby"]:
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
        platform_keywords = [
            "kubernetes", "docker", "cloud", "platform", "infra", "infrastructure",
            "devops", "terraform", "ansible", "aws", "gcp", "azure", "linux", "hosting",
            "deployment", "orchestration", "runtime", "database", "server", "backend",
            "service", "serverless", "queue", "stream", "broker", "gateway", "workflow",
            "monitoring", "observability",
        ]
        score += sum(1.0 for keyword in platform_keywords if keyword in text)
        score += sum(1.5 for topic in ["devops", "cloud", "infrastructure", "kubernetes", "platform"] if topic in topics)
        if domain in {"devops", "backend", "systems"}:
            score += 1.5

    elif target_quadrant == "tools":
        tool_keywords = ["tool", "cli", "editor", "plugin", "extension", "sdk", "framework", "library", "automation"]
        score += sum(1.0 for keyword in tool_keywords if keyword in text)
        score += sum(1.5 for topic in ["testing", "tool", "framework", "library"] if topic in topics)
        if domain in {"frontend", "backend"}:
            score += 0.5

    elif target_quadrant == "languages":
        if lang in ["python", "javascript", "typescript", "rust", "go", "java", "c#", "kotlin", "swift", "php", "ruby"]:
            score += 3.0
        score += sum(1.0 for keyword in ["language", "compiler", "runtime", "interpreter"] if keyword in text)
        if domain in {"systems", "data science"}:
            score += 0.5

    elif target_quadrant == "techniques":
        technique_keywords = [
            "guide", "roadmap", "tutorial", "book", "books", "course", "interview",
            "awesome", "algorithms", "patterns", "architecture", "best practices", "learning",
        ]
        score += sum(1.0 for keyword in technique_keywords if keyword in text)
        if domain == "general":
            score += 0.5

    return score
