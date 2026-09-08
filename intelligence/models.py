from dataclasses import dataclass, field
from enum import Enum
from scanner.models import RepositoryIndex

class Confidence(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    
@dataclass(slots=True)
class Indicator:
    name: str
    confidence: Confidence
    evidence: str

@dataclass(slots=True)
class RepositoryProfile:
    index: RepositoryIndex
    project_indicators: list[Indicator] = field(default_factory=list)
    build_systems: list[Indicator] = field(default_factory=list)
    frameworks: list[Indicator] = field(default_factory=list)
    dependencies: list[Indicator] = field(default_factory=list)
    embedded_indicators: list[Indicator] = field(default_factory=list)
