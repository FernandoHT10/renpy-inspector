# Security Policy

> 🌐 **Language**: English • [Español](#política-de-seguridad-en-español)

The **Ren'Py Inspector** team takes the security of our static analysis engine and our users' intellectual property seriously. This document outlines our security architecture, supported versions, and the process for responsibly reporting security vulnerabilities.

---

## 1. Security Architecture & Threat Model

Ren'Py Inspector is designed from the ground up to inspect potentially untrusted game scripts safely:

* **100% Static Execution (No Code Execution)**:
  Ren'Py visual novels downloaded from third-party sources may contain arbitrary Python code. Ren'Py Inspector treats all scripts (`.rpy`, `*_ren.py`) strictly as **untrusted text data**. It never uses `eval()`, `exec()`, or `compile()`, and never imports scripts into the Python runtime.
* **100% Local & Offline**:
  The inspector operates entirely on your local machine. It makes zero outbound network requests, collects no telemetry, and transmits no code or metadata. Your unreleased scripts, storylines, and assets remain completely confidential.
* **Path Traversal Defense**:
  All asset paths and script references are strictly validated and normalized against the project's root and `game/` directories, preventing directory traversal attacks (`../`).
* **HTML Report Sanitization**:
  The self-contained interactive HTML reporter automatically escapes all issue titles, locations, and code snippets to prevent Stored Cross-Site Scripting (XSS) when viewing reports in a browser.
* **ReDoS Protection**:
  All regular expressions in the lexer and parser are structured with linear-time or bounded evaluation to prevent Denial of Service via algorithmic complexity attacks (ReDoS).

---

## 2. Supported Versions

Only the latest stable release branch receives security updates:

| Version | Supported          | Status             |
| :------ | :----------------: | :----------------- |
| 1.0.x   | :white_check_mark: | Active / Current   |
| < 1.0.0 | :x:                | End of Life (EOL)  |

---

## 3. Reporting a Vulnerability

If you discover a security vulnerability or potential threat in Ren'Py Inspector, please report it responsibly so we can resolve it before public disclosure.

### How to Report

1. **GitHub Private Vulnerability Advisory (Recommended)**:
   Submit a confidential report directly via GitHub:
   [https://github.com/FernandoHT10/renpy-inspector/security/advisories/new](https://github.com/FernandoHT10/renpy-inspector/security/advisories/new)

2. **Email**:
   If private advisories are unavailable, contact the project maintainer directly via GitHub profile:
   [@FernandoHT10](https://github.com/FernandoHT10)

### What to Include

To help us investigate and patch the issue efficiently, please include:
* A detailed description of the vulnerability.
* The affected component (e.g., AST Parser, File Scanner, HTML Reporter, GUI).
* Step-by-step instructions or a minimal reproducible example (e.g., a sample `.rpy` script).
* The potential impact or attack vector.

### Response SLA

* **Initial Acknowledgement**: Within 48 hours.
* **Triage & Assessment**: Within 5 business days.
* **Fix & Coordinated Release**: Within 14 days, accompanied by a public security advisory and credit to the reporter.

---

## 4. Out of Scope

The following scenarios are considered out of scope for security reports:

* Vulnerabilities in third-party dependencies (e.g., Python itself, PySide6/Qt, or OS-level libraries), unless caused by our improper integration.
* Attacks requiring physical access to the local machine or compromised administrative privileges.
* Malformed Ren'Py scripts that cause parse errors or warnings without executing code or compromising the host environment (these should be reported as standard bug issues).

---

## Política de Seguridad (en Español)

El equipo de **Ren'Py Inspector** se compromete a garantizar la máxima seguridad y privacidad en el análisis de proyectos Ren'Py:

1. **Ejecución 100% Estática**: Jamás se ejecutan scripts del usuario ni se llama a `eval()`, `exec()` o `compile()`.
2. **Totalmente Local y Offline**: Sin telemetría ni peticiones externas a internet. La propiedad intelectual de tus juegos no sale de tu equipo.
3. **Protección contra Traversal y XSS**: Rutas normalizadas dentro del directorio `game/` y reporte HTML con sanitización estricta.
4. **Reporte Responsable**: Si encuentras una vulnerabilidad de seguridad, repórtala de forma privada a través del panel de [Asesorías de Seguridad de GitHub](https://github.com/FernandoHT10/renpy-inspector/security/advisories/new).
