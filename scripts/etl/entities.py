from dataclasses import dataclass, field


@dataclass
class CanonicalTechnology:
    """Canonical entity representing a technology in the radar.

    This class serves as the central data structure for tracking technologies,
    their aliases, associated repositories, packages, and ecosystems.
    It uses default factories to ensure empty sets/lists are properly initialized.

    Attributes:
        id: Unique identifier for the technology (e.g., "typescript", "react")
        display_name: Human-readable name (e.g., "TypeScript", "React")
        entity_type: Type of entity (e.g., "technology", "platform", "tool")
        aliases: Set of alternative names/abbreviations for the technology
        repos: Set of associated repository identifiers
        packages: Set of associated package identifiers (e.g., "npm:typescript")
        ecosystems: Set of ecosystems the technology belongs to (e.g., "npm", "pypi")
    """
    id: str
    display_name: str
    entity_type: str
    aliases: set[str] = field(default_factory=set)
    repos: set[str] = field(default_factory=set)
    packages: set[str] = field(default_factory=set)
    ecosystems: set[str] = field(default_factory=set)
