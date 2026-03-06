from dataclasses import dataclass, field


@dataclass
class CanonicalTechnology:
    id: str
    display_name: str
    entity_type: str
    aliases: set[str] = field(default_factory=set)
    repos: set[str] = field(default_factory=set)
    packages: set[str] = field(default_factory=set)
    ecosystems: set[str] = field(default_factory=set)
