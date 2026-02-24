from dataclasses import dataclass


@dataclass
class ETLConfig:
    sources: list[str]
    checkpoint_enabled: bool
    output_public: str
    output_internal: str