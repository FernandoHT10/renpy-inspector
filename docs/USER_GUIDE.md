# Ren'Py Inspector — User Guide & Manual

> 🌐 **Language / Idioma**: [English](USER_GUIDE.md) • [Español](USER_GUIDE.es.md) • [Home / README](../README.md)

Welcome to the official **Ren'Py Inspector** User Guide.

This manual explains how to use the tool across its graphical desktop interface (GUI), standalone Windows executable (`.exe`), and command-line interface (CLI), as well as how to integrate it into automated CI/CD workflows, configure custom rules, and build your own extensions.

---

## 1. Execution Modes

Ren'Py Inspector can be executed in three ways depending on your development environment:

### 1.1 Standalone Windows Executable (`RenPyInspector.exe`)
The standalone Windows version is 100% portable and requires **no Python installation, external libraries, or administrator privileges**:
* **Direct Launch (Non-Technical Users)**: Double-click `RenPyInspector.exe` in Windows Explorer to open the graphical desktop interface.
* **Portable Workflow**: You can copy `RenPyInspector.exe` to a flash drive or share it with narrative writers, translators, and QA testers who do not have Python set up.
* **Drag & Drop**: Drag any Ren'Py project folder directly onto the window to begin immediate inspection.
* **From PowerShell / Command Prompt**:
  ```powershell
  # Launch GUI
  .\RenPyInspector.exe

  # Open a specific project folder in the GUI immediately
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

# CI/CD Resilience: Permit scan to succeed even if some legacy files fail parsing
renpy-inspector "C:/Games/MyRenpyGame" --allow-partial

# Engine Debugging: Abort immediately on the first unhandled rule exception
renpy-inspector "C:/Games/MyRenpyGame" --fail-fast

# Rule Fault Tolerance: Continue scanning and record rule failures without crashing
renpy-inspector "C:/Games/MyRenpyGame" --allow-rule-failures
```

> **Compatibility Note**: All options can be run using either the `renpy-inspector` executable or standard Python module syntax `python -m renpy_inspector`.

### Complete CLI Argument Reference

| Flag / Option | Argument | Description |
| :--- | :--- | :--- |
| `project_path` | `<path>` | Path to the Ren'Py project root folder (or directly the `game/` folder). |
| `--gui` | *None* | Launch the desktop graphical user interface. |
| `--show-info` | *None* | Display `INFO` severity notices (such as potentially unused assets). |
| `--severity` | `CRITICAL\|ERROR\|WARNING\|INFO` | Minimum severity threshold to report and gate on. |
| `--category` | `<name>` | Filter issues by problem domain (`Code`, `Assets`, `Audio`, `Images`, `Translation`, `References`). |
| `--export-html` | `<path.html>` | Save a 100% self-contained interactive HTML report. |
| `--export-json` | `<path.json>` | Save a versioned structured JSON report (Schema v2.0.0). |
| `--allow-partial` | *None* | Permits the scan to return exit code 0/1 even if some files could not be parsed. |
| `--allow-rule-failures`| *None* | Catches and records unexpected rule exceptions without crashing the runner. |
| `--fail-fast` | *None* | Aborts the scan immediately upon encountering the first rule exception. |
| `--version` | *None* | Display the current Ren'Py Inspector version. |

### Standard Exit Codes (CI/CD Pipeline Integration)

Ren'Py Inspector uses standard deterministic exit codes for continuous integration pipelines:

* `0` (**EXIT_SUCCESS**): The project is clean, or discovered issues are below the configured severity threshold (or `--allow-partial` / `--allow-rule-failures` was specified when tolerated).
* `1` (**EXIT_ISSUES_FOUND**): One or more defects meeting or exceeding the configured severity threshold (by default, any `CRITICAL` or `ERROR`) were discovered in game scripts or assets.
* `2` (**EXIT_ERROR**): Execution or system failure:
  - The specified project directory is not a valid Ren'Py game folder.
  - A fatal unhandled rule exception occurred (without `--allow-rule-failures`).
  - Analysis was `PARTIAL` due to parse/scanner errors (without `--allow-partial`).
  - The analysis was cancelled.

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

---

## 9. Frequently Asked Questions (FAQ) & Troubleshooting

### Q1: Why does Ren'Py Inspector flag an audio file as missing if it plays fine on Windows?
**A**: Windows has a case-insensitive filesystem (`music/Theme.ogg` and `music/theme.ogg` resolve to the same file), but Linux, macOS, Android, and Steam Deck use case-sensitive filesystems. If the filename case in your script does not match the actual file on disk, Ren'Py will crash on Steam Deck or Linux. Rule `RPY-REF-001` checks for exact character case to protect cross-platform builds.

### Q2: How does the inspector resolve audio files played via `audio.<name>`?
**A**: Ren'Py automatically places audio files placed directly inside `game/audio/` into the `audio` store namespace. For example, `game/audio/bgm_battle.ogg` can be played as `play music audio.bgm_battle`. Ren'Py Inspector fully models this behavior and matches `audio.<symbol>` references directly against candidate files in `game/audio/`, preventing false missing audio warnings.

### Q3: How do I handle audio playback clauses like `<loop 0>` or `<from 10.5>`?
**A**: Ren'Py Inspector strips and parses playback clauses (e.g., `play music "<loop 2.5>audio/music.ogg"`) before validating file existence on disk, correctly isolating the clean file path.

### Q4: How can I exclude third-party libraries, test folders, or translation templates?
**A**: Create a `renpy-inspector.toml` file in your project root:
```toml
[tool.renpy-inspector]
ignore_patterns = [
    "game/tl/None/**",       # Default Ren'Py template folder
    "game/python-packages/**",
    "game/test/**",
]
```

### Q5: Can I share reports with team members who don't have Python or the tool installed?
**A**: Yes! In the desktop GUI, click **Export HTML**, or run the CLI with `--export-html report.html`. The generated file is completely standalone (100% self-contained with no external CSS, fonts, or JS CDNs) and can be opened in any web browser.

### Q6: My project contains legacy or corrupted scripts that fail parsing. How can I still audit the rest of the game?
**A**: In the CLI, pass the `--allow-partial` flag:
```bash
renpy-inspector "C:/Games/MyProject" --allow-partial
```
This allows the engine to record the unparseable files as diagnostics while executing all static QA rules across all remaining valid scripts, returning standard exit codes (0/1).
