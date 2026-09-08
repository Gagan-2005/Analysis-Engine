from intelligence.models import Indicator, Confidence, RepositoryProfile

def detect_frameworks_and_indicators(profile: RepositoryProfile) -> None:
    """
    Evaluates build systems and dependencies to infer frameworks and embedded indicators.
    Modifies the profile in-place.
    """
    
    # 1. Embedded Indicators
    has_ino = any(f.extension.lower() == ".ino" for f in profile.index.files)
    if has_ino:
        profile.embedded_indicators.append(Indicator(
            name="Arduino indicators detected",
            confidence=Confidence.HIGH,
            evidence="Found .ino sketch files"
        ))
        
    has_pio = any(b.name == "PlatformIO" for b in profile.build_systems)
    if has_pio:
        profile.embedded_indicators.append(Indicator(
            name="Embedded C/C++ indicators detected",
            confidence=Confidence.HIGH,
            evidence="Found platformio.ini"
        ))
        
    for dep in profile.dependencies:
        if dep.name in {"WiFi.h", "ESP32", "Arduino.h", "PubSubClient.h"}:
            profile.embedded_indicators.append(Indicator(
                name="ESP32-related indicators detected" if dep.name == "WiFi.h" else "Arduino-related dependencies detected",
                confidence=Confidence.MEDIUM,
                evidence=f"Found dependency: {dep.name}"
            ))

    # 2. Project Frameworks
    has_python = any(l.language == "Python" for l in profile.index.languages)
    has_c = any(l.language in {"C", "C++", "C Header", "C++ Header"} for l in profile.index.languages)
    has_web = any(l.language in {"HTML", "CSS", "JavaScript"} for l in profile.index.languages)
    
    if has_python:
        profile.project_indicators.append(Indicator(
            name="Python Project",
            confidence=Confidence.HIGH,
            evidence="Python files detected"
        ))
        
    if has_c and not has_ino:
        profile.project_indicators.append(Indicator(
            name="C/C++ Project",
            confidence=Confidence.HIGH,
            evidence="C/C++ files detected"
        ))
        
    if has_web:
        profile.project_indicators.append(Indicator(
            name="Web Project",
            confidence=Confidence.MEDIUM,
            evidence="Web assets (HTML/CSS/JS) detected"
        ))

