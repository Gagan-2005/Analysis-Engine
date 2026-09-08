from planner.models import AnalyzerType
from intelligence.models import RepositoryProfile

# Declarative mapping of programming languages to their required static analysis tools.
_LANGUAGE_ANALYZERS = {
    # Backend
    "Python": [
        AnalyzerType.SONARQUBE,
    ],
    
    # Embedded / Systems
    "C": [
        AnalyzerType.CPPCHECK,
    ],
    "C++": [
        AnalyzerType.CPPCHECK,
    ],
    
    # Web
    "HTML": [
        AnalyzerType.SONARQUBE,
    ],
    "CSS": [
        AnalyzerType.SONARQUBE,
    ],
    "JavaScript": [
        AnalyzerType.SONARQUBE,
    ],
    "TypeScript": [
        AnalyzerType.SONARQUBE,
    ],
}


def get_analyzers(language: str, profile: RepositoryProfile) -> list[AnalyzerType]:
    """
    Retrieves the list of static analysis tools configured for a given programming language.
    Uses Repository Intelligence to conditionally append tools (e.g., Arduino CLI).
    """
    analyzers = list(_LANGUAGE_ANALYZERS.get(language, ()))
    
    # Intelligence-based rules
    has_arduino_indicators = any("Arduino" in ind.name or "ESP32" in ind.name for ind in profile.embedded_indicators)
    
    if language in {"Arduino", "C++", "C"} and has_arduino_indicators:
        if AnalyzerType.ARDUINO_CLI not in analyzers:
            analyzers.append(AnalyzerType.ARDUINO_CLI)
            
    # Always run Cppcheck for C/C++/Arduino
    if language == "Arduino" and AnalyzerType.CPPCHECK not in analyzers:
        analyzers.append(AnalyzerType.CPPCHECK)
        
    return analyzers
