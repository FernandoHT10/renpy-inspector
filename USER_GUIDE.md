# Ren'Py Inspector — User Guide & Manual

> 🌐 **Language / Idioma**: [English](USER_GUIDE.md) • [Español](USER_GUIDE.es.md)

Welcome to the official **Ren'Py Inspector** User Guide.

This manual explains how to use the tool across its graphical desktop interface (GUI), standalone Windows executable (`.exe`), and command-line interface (CLI), as well as how to integrate it into automated CI/CD workflows, configure custom rules, and build your own extensions.

---

## 1. Execution Modes

Ren'Py Inspector can be executed in three ways depending on your development environment:

### 1.1 Standalone Windows Executable (`RenPyInspector.exe`)
If you downloaded or built the standalone Windows version, you do not need Python or any external dependencies:
* **Double-click**: Double-click `RenPyInspector.exe` in Windows Explorer to open the graphical user interface directly.
* **From PowerShell / Command Prompt**:
  ```powershell
  .\RenPyInspector.exe
  # Or open a specific project folder directly
  .\RenPyInspector.exe "C:\Games\MyRenpyGame"
  ```

### 1.2 Python Desktop GUI (PySide6 / Qt6)
If you are working inside a Python virtual environment:
```bash
# Launch the desktop GUI directly
renpy-inspector-gui

# Or via Python module syntax
python -m renpy_inspector --gui "C:/Games/MyRenpyGame"
```

### 1.3 Command-Line Interface (CLI)
Ideal for continuous integration, developer terminals, and build scripts:
```bash
# Option 1: Direct console executable
renpy-inspector "C:/Games/MyRenpyGame"

# Option 2: Python module execution
python -m renpy_inspector "C:/Games/MyRenpyGame"
```

---

## 2. Desktop Graphical Interface Guide

### 2.1 Selecting and Loading a Project
1. **📁 Browse Button**: Click to open a directory picker and select your Ren'Py project root (or directly its `game/` folder).
2. **Drag & Drop**: Drag your game folder directly from Windows Explorer or macOS Finder onto the Ren'Py Inspector window.
3. **Status Indicator**:
   * <span style="color:#3fb950; font-weight:bold;">Green</span>: Valid Ren'Py `game/` directory detected. Ready to inspect.
   * <span style="color:#e3b341; font-weight:bold;">Yellow</span>: The selected folder does not appear to contain a standard Ren'Py structure.
4. Click **🔍 Inspect Project** to start the analysis.

### 2.2 Asynchronous Background Evaluation
During inspection, the app runs analysis in a dedicated background worker (`QThread`) keeping the UI completely fluid and responsive:
* The progress bar displays real-time progress from $0\% \to 100\%$.
* The status label dynamically reports which static rule is currently being evaluated (e.g., `Evaluating rule 7/20: Unreachable Code Statement...`).

### 2.3 Metric Summary Cards Dashboard
Once the scan completes (typically in under 1 second), the dashboard displays:
* **TOTAL ISSUES**: Overall number of problems discovered.
* **ERRORS / CRITICAL**: Severe issues that will crash the game at runtime or break script flow (e.g., jumps to missing labels, undefined screens, or persistent variables declared with `define`).
* **WARNINGS**: Potential inconsistencies and risks (e.g., cross-platform casing discrepancies between Windows and Linux/Steam Deck, duplicate screens, or unclosed dialogue formatting tags).
* **INFO / TIPS**: Clean-up opportunities (e.g., unused image or audio files on disk, or unreferenced labels).
* **SCANNED IN**: Exact processing duration in seconds.

> **Productivity Tip**: Click any metric card (**TOTAL**, **ERRORS**, **WARNINGS**, **INFO**) to instantly filter the issues table with a single click.

### 2.4 Multi-Criteria Live Filtering
The toolbar above the table allows combining dynamic filters in real time:
* **Text Search**: Type any search query (e.g., `script.rpy`, `RPY-CODE-001`, `screen`, `menu`) to filter issues as you type.
* **Severity Filter**: Filter by `All Severities`, `CRITICAL`, `ERROR`, `WARNING`, or `INFO`.
* **Category Filter**: Filter by specific problem domains:
  * `Code`: Narrative logic, jumps, calls, menus, labels, dead code, and persistence.
  * `Assets`: Font files, audio channels, and orphan files.
  * `Audio`: Missing music, sound effect, and voice files.
  * `Images`: Missing explicit image declarations.
  * `Translation`: Localization blocks and untranslated dialogues.
  * `References`: Cross-platform casing differences between script code and filesystem.
* **Reset Filters**: Clears all filters and restores the complete issue list.

### 2.5 Detailed Diagnostics Inspector Pane
Selecting any issue in the table populates the right-hand panel:
1. **Severity Badge & Rule ID**: Canonical identifier (e.g., `RPY-CODE-008`).
2. **Issue Title**: Concise summary of the defect.
3. **File Location**: Relative path and line number (`game/script.rpy:L45`).
4. **Description**: In-depth technical explanation of why Ren'Py will fail or misbehave.
5. **Source Code Snippet**: Extracted source code with syntax highlighting in a monospaced view.
6. **Recommended Action (`💡 RECOMMENDED ACTION`)**: Direct, actionable instruction on how to resolve the issue.

### 2.6 Report Exporting
Located in the upper right corner of the window:
* **Export HTML**: Produces an interactive single-file `.html` report (100% self-contained, zero CDN dependencies) with client-side JavaScript search, severity filtering, and dark mode responsive layout.
* **Export JSON**: Generates a versioned v1.0.0 structured `.json` file for integration with internal QA dashboards or custom analytics tools.

---

## 3. Command-Line Interface (CLI) Guide

Ren'Py Inspector provides a fast, full-featured CLI suitable for automation and continuous integration:

### Common Commands
```bash
# Standard project inspection
renpy-inspector "C:/Games/MyRenpyGame"

# Display INFO severity issues (such as unused assets on disk)
renpy-inspector "C:/Games/MyRenpyGame" --show-info

# Filter by minimum severity threshold (CRITICAL, ERROR, WARNING, INFO)
renpy-inspector "C:/Games/MyRenpyGame" --severity ERROR

# Filter by domain category (Code, Assets, Translation, etc.)
renpy-inspector "C:/Games/MyRenpyGame" --category Code

# Export automated standalone HTML and structured JSON reports
renpy-inspector "C:/Games/MyRenpyGame" --export-html "reports/qa.html" --export-json "reports/qa.json"
```

> **Compatibility Note**: All options can be run using either the `renpy-inspector` executable or standard Python module syntax `python -m renpy_inspector`.

### Standard Exit Codes (CI/CD)
* `0`: Clean project with zero issues meeting or exceeding the configured severity threshold.
* `1`: The project contains one or more critical errors (or issues meeting the `--severity` threshold), or the target path is not a valid Ren'Py project.

---

## 4. Static QA Rules Reference (20 Core Rules)

| Rule ID | Name | Severity | Category |
| :--- | :--- | :--- | :--- |
| `RPY-CODE-001` | Broken Jump Target | `ERROR` | Code |
| `RPY-CODE-002` | Broken Call Target | `ERROR` | Code |
| `RPY-CODE-003` | Duplicate Label Definition | `ERROR` | Code |
| `RPY-CODE-004` | Conflicting Define/Default | `WARNING` | Code |
| `RPY-CODE-005` | Unused Label | `INFO` | Code |
| `RPY-CODE-006` | Shadowed Ren'Py Built-in | `WARNING` | Code |
| `RPY-CODE-007` | Unreachable Code Statement | `WARNING` | Code |
| `RPY-CODE-008` | Persistent Variable with Define | `ERROR` | Code |
| `RPY-CODE-009` | Empty Menu Statement | `ERROR` | Code |
| `RPY-CODE-010` | Invalid Init Priority | `WARNING` | Code |
| `RPY-SCREEN-001` | Undefined Screen | `ERROR` | Code |
| `RPY-SCREEN-002` | Duplicate Screen Definition | `WARNING` | Code |
| `RPY-AUDIO-001` | Missing Audio File | `ERROR` | Audio |
| `RPY-AUDIO-002` | Invalid Audio Channel | `WARNING` | Assets |
| `RPY-IMAGE-001` | Missing Image File | `ERROR` | Images |
| `RPY-FONT-001` | Missing Font File | `ERROR` | Assets |
| `RPY-REF-001` | Asset Case Mismatch | `WARNING` | References |
| `RPY-TL-001` | Missing Translation Block | `WARNING` | Translation |
| `RPY-ASSET-001` | Potentially Unused Asset | `INFO` | Assets |
| `RPY-TEXT-001` | Unclosed Text Tag in Dialogue | `WARNING` | Code |

---

## 5. Custom Configuration (`renpy-inspector.toml`)

You can customize rules and scanner behavior by placing a `renpy-inspector.toml` file in your game root directory (or configuring `[tool.renpy-inspector]` in `pyproject.toml`):

```toml
[tool.renpy-inspector]
# Disable specific rules
disabled_rules = [
    "RPY-ASSET-001",  # Ignore unreferenced asset candidates
]

# Ignore specific paths or cache directories
ignore_patterns = [
    "game/tl/None/**",
    "game/cache/**",
]

# Register custom game audio channels
custom_audio_channels = [
    "ambient",
    "sfx_loop",
]

# Override rule severity levels
[tool.renpy-inspector.severity_overrides]
"RPY-CODE-007" = "ERROR"   # Treat unreachable code as critical error
```

---

## 6. Continuous Integration (GitHub Actions)

To automatically audit every commit or pull request before publishing your game, create `.github/workflows/renpy_inspector.yml`:

```yaml
name: Ren'Py QA Static Inspection

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  inspect:
    runs-on: ubuntu-latest

    steps:
    - name: Check out repository
      uses: actions/checkout@v4

    - name: Set up Python 3.11
      uses: actions/setup-python@v5
      with:
        python-version: "3.11"

    - name: Install Ren'Py Inspector
      run: |
        pip install renpy-inspector

    - name: Run Static Analysis
      run: |
        renpy-inspector . --export-html qa_report.html --export-json qa_report.json

    - name: Upload QA Report Artifacts
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: renpy-qa-report
        path: |
          qa_report.html
          qa_report.json
```

---

## 7. Windows Standalone Executable Compilation

To compile a standalone `.exe` binary on Windows:

```powershell
# Build with PowerShell script
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1

# Or build directly with Python
python scripts/build_windows.py
```

The resulting standalone executable will be located at `dist/RenPyInspector.exe`.

---

## 8. Developer Edition: Creating Custom Rules

In the **Developer Edition**, studios can implement specialized in-house static analysis rules by placing `.py` files into a plugins directory:

```python
from renpy_inspector.core.rules.base import BaseRule
from renpy_inspector.core.models.enums import Category, Severity
from renpy_inspector.core.models.issue import Issue
from renpy_inspector.core.models.location import Location

class RequireMusicVolumeInitRule(BaseRule):
    rule_id = "STUDIO-AUDIO-001"
    title = "Default Music Volume Required"
    category = Category.CODE
    default_severity = Severity.WARNING
    description = "Ensures the game defines default music volume in preferences."

    def analyze(self, context) -> list[Issue]:
        issues = []
        has_volume_config = any(
            v.name == "config.default_music_volume" for v in context.all_variables
        )
        if not has_volume_config:
            loc = Location(file_path="game/options.rpy", line_number=1)
            issues.append(
                self.create_issue(
                    message="Variable 'config.default_music_volume' is not defined.",
                    location=loc,
                    suggestion="Add 'define config.default_music_volume = 0.8' to options.rpy.",
                )
            )
        return issues
```

The dynamic plugin loader will automatically discover and register your rule, making it available in both the CLI and desktop GUI.
