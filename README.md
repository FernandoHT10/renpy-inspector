# Ren'Py Inspector

> 🌐 **Language**: [English](README.md) • [Español](README.es.md)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![GUI: PySide6](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-success.svg)](https://wiki.qt.io/Qt_for_Python)
[![Static Analysis](https://img.shields.io/badge/analysis-100%25%20Static%20%26%20Safe-brightgreen.svg)]()
[![Rules: 20 Core](https://img.shields.io/badge/rules-20%20Core%20Rules-blueviolet.svg)]()
[![Tests: 113 Passed](https://img.shields.io/badge/tests-113%20passing%20(100%25)-brightgreen.svg)]()
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Platform: Windows | Linux | macOS](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![License: Commercial](https://img.shields.io/badge/license-Commercial-informational.svg)]()

**Ren'Py Inspector** is an enterprise-grade desktop GUI and CLI static analysis, quality assurance (QA), and continuous auditing platform engineered specifically for visual novel developers and studios building on the [Ren'Py](https://www.renpy.org/) engine.

It thoroughly validates Ren'Py projects of any scale to detect broken narrative jumps, missing or orphaned assets, cross-platform casing mismatches (Linux/Steam Deck/macOS vs. Windows), conflicting define/default declarations, fatal persistence bugs, empty menu choices, unreachable dead code, duplicate screens, and unclosed text dialogue formatting tags **before compiling or publishing the game**.

For a detailed step-by-step walkthrough, see the [User Guide (USER_GUIDE.md)](USER_GUIDE.md).

---

## 1. Architecture & Security Principles

* **100% Static & Safe**: Treats game scripts as **untrusted data** (`SCAN → ANALYZE → REPORT`). It never calls `eval()`, `exec()`, or `compile()`, and never imports `.rpy` scripts or user Python code into runtime.
* **Zero Code Modification**: Strictly read-only operations. It never alters, rewrites, or mutates any user project files.
* **Completely Local & Offline**: Zero internet connectivity, zero telemetry. All scripts, assets, and metadata are processed entirely on your local machine, protecting your intellectual property.
* **High-Performance Determinism**: Pure Python lexical-syntactic engine capable of scanning and analyzing massive projects with 2,000+ `.rpy` scripts and tens of thousands of assets in under 22 seconds.

---

## 2. Key Features

### Desktop Graphical Interface (PySide6 / Qt6)
* **Modern Dark Theme**: Professional developer-focused UI inspired by Linear and VS Code.
* **Drag & Drop Support**: Drop your Ren'Py project folder directly onto the window for instant inspection.
* **Interactive Metric Cards**: Real-time summary counters for *Total Issues*, *Errors / Critical*, *Warnings*, *Info / Tips*, and *Scan Duration (seconds)*, featuring 1-click table filtering.
* **Live Multi-Criteria Filtering**:
  * Real-time search across rule ID, title, error message, or filename.
  * Dynamic severity selector (`CRITICAL`, `ERROR`, `WARNING`, `INFO`).
  * Dynamic category selector (`Code`, `Assets`, `Audio`, `Images`, `Translation`, `References`).
* **Interactive Issues Table**: Sortable table with color-coded severity badges, rule identifiers, titles, disk locations (`game/...:LXX`), and categories.
* **Detailed Diagnostics Pane**:
  * Monospaced code snippet viewer showing original source code with contextual line numbers.
  * Prominent **Recommended Action** (`RECOMMENDED ACTION`) box providing direct copy-pasteable fix instructions.
  * Exact file location and rule metadata.
* **Non-Blocking Async Worker (`QThread`)**: Smooth progress bar showing live evaluation of each of the 20 rules step-by-step with instant cancellation support.
* **Direct 1-Click Exporters**: Native buttons to export standalone interactive HTML reports and structured JSON data.

### CLI Tool for CI/CD Automation & Pipelines
* Formatted terminal output with clean statistical breakdown and categorized notices.
* Standard POSIX exit codes to automatically fail continuous integration builds on critical errors (`exit 1` on critical issues; `exit 0` when clean).
* `--severity`, `--category`, `--show-info`, `--export-json`, and `--export-html` flags for headless workflows.

### Autonomous Multi-Format Reporting
* **Interactive Standalone HTML Report**: Single, self-contained `.html` file (zero CDN dependencies, embedded CSS/JS) featuring client-side search, severity filters, and responsive design to share with scriptwriters, artists, or translators.
* **Structured JSON Report**: Versioned v1.0.0 schema ready for ingestion into custom QA dashboards, SonarQube, or analytics pipelines.

### Windows Standalone Executable (.exe)
* Optimized PyInstaller specification (`renpy_inspector.spec`) and build scripts to generate a single-file portable `.exe` that runs without requiring Python on target machines.

---

## 3. Complete QA Rules Catalog (20 Core Rules)

Ren'Py Inspector features **20 deterministic static analysis rules** across 6 categories:

| Rule ID | Name | Severity | Category | Tier | Description & Detection |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RPY-CODE-001` | **Broken Jump Target** | `ERROR` | Code | Free | Detects `jump` statements targeting labels that do not exist in the project. |
| `RPY-CODE-002` | **Broken Call Target** | `ERROR` | Code | Free | Detects `call` statements referencing labels that are not defined. |
| `RPY-CODE-003` | **Duplicate Label Definition** | `ERROR` | Code | Free | Detects identical label definitions across multiple `.rpy` script files. |
| `RPY-CODE-004` | **Conflicting Define/Default** | `WARNING` | Code | Free | Warns when a variable is declared with both `define` (constant) and `default` (mutable). |
| `RPY-CODE-005` | **Unused Label** | `INFO` | Code | Pro | Identifies defined labels that are never reached by jumps, calls, or menus. |
| `RPY-CODE-006` | **Shadowed Ren'Py Built-in** | `WARNING` | Code | Pro | Warns when user variables shadow core Ren'Py engine globals (`renpy`, `config`, `store`, `persistent`). |
| `RPY-CODE-007` | **Unreachable Code Statement** | `WARNING` | Code | Free | Detects dialogue or statements immediately following an unconditional `jump` or `return` without an intervening label. |
| `RPY-CODE-008` | **Persistent Variable with Define** | `ERROR` | Code | Free | Detects `persistent.*` variables declared using `define` instead of `default` (which resets persistence on every launch). |
| `RPY-CODE-009` | **Empty Menu Statement** | `ERROR` | Code | Free | Detects `menu:` blocks without selectable choice items, which causes a fatal Ren'Py runtime crash. |
| `RPY-CODE-010` | **Invalid Init Priority** | `WARNING` | Code | Free | Warns when `init` priorities fall outside the safe user range (-999 to 999), reserved for internal engine code. |
| `RPY-SCREEN-001` | **Undefined Screen** | `ERROR` | Code | Pro | Detects `call screen`, `show screen`, or `hide screen` statements referencing nonexistent screens. |
| `RPY-SCREEN-002` | **Duplicate Screen Definition** | `WARNING` | Code | Free | Detects screens defined multiple times with the same name and variant, causing silent overwriting. |
| `RPY-AUDIO-001` | **Missing Audio File** | `ERROR` | Audio | Free | Detects music, sound, or voice audio files referenced in `play`/`queue` statements missing from disk. |
| `RPY-AUDIO-002` | **Invalid Audio Channel** | `WARNING` | Assets | Pro | Detects unrecognized or mistyped audio channels outside standard channels (`music`, `sound`, `voice`, `audio`). |
| `RPY-IMAGE-001` | **Missing Image File** | `ERROR` | Images | Free | Detects explicit `image` declarations pointing to file paths that do not exist on disk. |
| `RPY-FONT-001` | **Missing Font File** | `ERROR` | Assets | Free | Detects font files declared in `gui.*` or scripts missing from the `game/` folder. |
| `RPY-REF-001` | **Asset Case Mismatch** | `WARNING` | References | Pro | Detects file path casing differences between script code and disk (prevents crashes on Linux, Steam Deck & macOS). |
| `RPY-TL-001` | **Missing Translation Block** | `WARNING` | Translation | Pro | Detects dialogue translation blocks present in some target languages but missing in others. |
| `RPY-ASSET-001` | **Potentially Unused Asset** | `INFO` | Assets | Pro | Identifies image and audio files on disk that have no static references across all project scripts. |
| `RPY-TEXT-001` | **Unclosed Text Tag in Dialogue** | `WARNING` | Code | Free | Detects dialogue text formatting tags (`{b}`, `{i}`, `{color=...}`, `{size=...}`) opened but never closed. |

---

## 4. Advanced Parser & Inference Engine Capabilities

Ren'Py Inspector goes far beyond basic regex search; it features a dedicated parser with deep engine semantics:

1. **Recursive Audio Stem Resolution**:
   Ren'Py permits playing audio using only a short stem name, resolving files automatically inside `game/audio/`, `game/voice/`, `game/music/`, or nested subdirectories. The inspector recursively indexes stems to avoid false alarms.

2. **Hierarchical Image Tag & Directory Resolution**:
   Supports Ren'Py's image naming conventions where `show eileen happy` can match both `game/images/eileen happy.png` and subdirectories like `game/images/eileen/happy.png`.

3. **Screen Actions & Runtime Invocations**:
   Inspects button actions such as `action [Jump("chapter_2"), Show("inventory_menu")]`, as well as Python runtime invocations (`renpy.jump("...")`, `renpy.call("...")`, `renpy.show_screen("...")`).

4. **Multiline Screen Signatures**:
   Parses complex screen definitions with multiple default arguments and tuples spanning across multiple physical lines.

5. **Menus with Arguments & Inline Named Menus**:
   Supports screen arguments (`menu (screen="choice_wheel"):`), choice arguments (`"Option" (arg=True):`), and inline named menus (`menu branch_selector:`), preventing false unused label warnings.

6. **Dialogue Formatting Tag Validator**:
   Validates standard Ren'Py text tags (`{b}`, `{i}`, `{u}`, `{s}`, `{size}`, `{color}`, `{font}`, `{cps}`, `{alpha}`) while ignoring self-closing tags (`{w}`, `{p}`, `{nw}`, `{fast}`) and escaped double brackets.

7. **Translation Template Filtering**:
   Automatically identifies reference template folders like `game/tl/None` to avoid emitting spurious missing translation warnings.

8. **Modern Format Support**:
   * **Images**: `.png`, `.jpg`, `.jpeg`, `.webp`, `.avif`, `.svg`.
   * **Audio**: `.mp3`, `.ogg`, `.opus`, `.wav`, `.flac`.
   * **Fonts**: `.ttf`, `.otf`.

---

## 5. Performance & Scalability (Production Benchmark)

Ren'Py Inspector is built to meet the needs of commercial game studios, delivering near-instant static analysis across projects of all scales:

### Scanning Speeds by Project Scale

| Project Scale | Typical Scripts | Multimedia Assets | Average Scan Duration | Recommended Use Cases |
| :--- | :---: | :---: | :---: | :--- |
| **Demo / Prototype** | < 25 scripts | Up to 500 assets | **< 0.1 seconds** | Game jams, proof of concepts, playable demos |
| **Standard Visual Novel** | 25 to 150 scripts | 500 to 5,000 assets | **0.3 to 0.8 seconds** | Narrative visual novels, kinetic novels |
| **Large Commercial Game** | 150 to 500 scripts | 5,000 to 15,000 assets | **1.2 to 2.8 seconds** | Branching visual novels, minigames, full voice acting |
| **Massive Production / RPG** | 500 to 1,000+ scripts | 15,000 to 35,000+ assets | **3.5 to 6.5 seconds** | Open-world or complex mechanic Ren'Py productions |

### Reliability Metrics
* **Stress-Tested Scale**: Validated on test suites spanning over **2,800 script files** and **95,000+ multimedia assets**.
* **High Throughput**: Sustained analysis rate exceeding **120 scripts per second** on standard developer hardware.
* **Low Memory Footprint**: Read-only static analysis avoids loading heavy audio/video media into RAM.
* **100% Deterministic**: Identical, reproducible results across Windows, macOS, and Linux.

---

## 6. Installation & Prerequisites

### System Requirements
* Windows 10/11, macOS 12+, or Linux x86_64.
* Python 3.11 or higher.
* PySide6 6.5+ (included in dependencies).

### Development Installation
```bash
# Clone or navigate to the repository directory
cd renpy_inspector

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

---

## 7. Quick Usage Guide

### Desktop GUI
To launch the graphical interface:

```bash
# Launch the desktop application directly
renpy-inspector-gui

# Or inspect a specific project directly from terminal
renpy-inspector --gui "C:/Games/MyRenpyGame"
```

### Command-Line Interface (CLI)
Ideal for fast local checks or continuous integration pipelines:

```bash
# Standard project inspection
renpy-inspector "C:/Games/MyRenpyGame"

# Display INFO severity issues (such as unused assets)
renpy-inspector "C:/Games/MyRenpyGame" --show-info

# Filter by minimum severity threshold (CRITICAL, ERROR, WARNING, INFO)
renpy-inspector "C:/Games/MyRenpyGame" --severity ERROR

# Filter by category (Code, Assets, Translation, etc.)
renpy-inspector "C:/Games/MyRenpyGame" --category Code

# Export automated interactive HTML and structured JSON reports
renpy-inspector "C:/Games/MyRenpyGame" --export-html qa_report.html --export-json qa_report.json
```

---

## 8. Windows Standalone Executable (.exe)

Ren'Py Inspector includes a PyInstaller specification (`renpy_inspector.spec`) to build a 100% standalone, portable `.exe` that runs without Python installed:

```powershell
# Option 1: Build with automated PowerShell script
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1

# Option 2: Build directly with Python
python scripts/build_windows.py
```

The optimized binary will be generated at:
```text
dist/RenPyInspector.exe
```

---

## 9. Custom Configuration (`renpy-inspector.toml`)

Customize rules and scanning behavior by creating a `renpy-inspector.toml` file in your game root (or under `[tool.renpy-inspector]` in `pyproject.toml`):

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

# Register custom audio channels used by your game
custom_audio_channels = [
    "ambient",
    "effects",
    "movie",
]

# Override rule severity levels
[tool.renpy-inspector.severity_overrides]
"RPY-CODE-007" = "ERROR"   # Elevate unreachable code to critical error
"RPY-REF-001"  = "ERROR"   # Enforce strict cross-platform casing match
```

---

## 10. Automated Test Suite & Quality Assurance

The project features a comprehensive test suite validating all 20 rules, the parsing engine, file cataloging, reporting modules, headless GUI components, and Windows packaging:

```bash
# Run all 113 automated tests
pytest

# Run tests with detailed code coverage report
pytest --cov=renpy_inspector

# Check code style and linting with ruff
ruff check .
```

---

## 11. License & Support

Copyright © 2026. All rights reserved.
Developed for the Ren'Py visual novel community and game development studios worldwide.
