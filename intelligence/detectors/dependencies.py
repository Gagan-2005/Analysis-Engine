import re
from scanner.models import RepositoryIndex
from intelligence.models import Indicator, Confidence

# Simple regex for #include and import statements
# E.g. #include <WiFi.h> or import flask
INCLUDE_REGEX = re.compile(r'^\s*#include\s*[<"]([^>"]+)[>"]')
PYTHON_IMPORT_REGEX = re.compile(r'^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)')

def extract_dependencies(index: RepositoryIndex) -> list[Indicator]:
    indicators = []
    extracted = set()
    
    # Only read a bounded number of lines to avoid performance issues
    MAX_LINES = 100
    
    for f in index.files:
        # Only process known source languages that we care about
        if f.language in {"Python", "C", "C++", "C Header", "C++ Header", "Arduino"}:
            try:
                with open(f.absolute_path, "r", encoding="utf-8", errors="ignore") as file_obj:
                    for i, line in enumerate(file_obj):
                        if i >= MAX_LINES:
                            break
                        
                        if f.language == "Python":
                            match = PYTHON_IMPORT_REGEX.search(line)
                            if match:
                                dep = match.group(1).split(".")[0]  # Only get top level module
                                if dep not in extracted:
                                    extracted.add(dep)
                                    indicators.append(Indicator(
                                        name=dep,
                                        confidence=Confidence.MEDIUM,
                                        evidence=f"Found 'import {dep}' in {f.relative_path}"
                                    ))
                        else:
                            # C-family
                            match = INCLUDE_REGEX.search(line)
                            if match:
                                dep = match.group(1)
                                if dep not in extracted:
                                    extracted.add(dep)
                                    indicators.append(Indicator(
                                        name=dep,
                                        confidence=Confidence.HIGH,
                                        evidence=f"Found '#include <{dep}>' in {f.relative_path}"
                                    ))
            except OSError:
                pass
                
    return indicators
