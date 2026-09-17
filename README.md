# Ren'Py Inspector

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![GUI: PySide6](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-success.svg)](https://wiki.qt.io/Qt_for_Python)
[![Static Analysis](https://img.shields.io/badge/analysis-100%25%20Static%20%26%20Safe-brightgreen.svg)]()
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: Commercial / Proprietary](https://img.shields.io/badge/license-Commercial-informational.svg)]()

**Ren'Py Inspector** es una plataforma profesional de escritorio y CLI para análisis estático y aseguramiento de calidad (QA) diseñada específicamente para estudios y desarrolladores de novelas visuales construidas sobre el motor [Ren'Py](https://www.renpy.org/).

Permite validar proyectos Ren'Py de forma exhaustiva para detectar errores de flujo narrativo, referencias rotas, assets faltantes o huérfanos, inconsistencias de mayúsculas/minúsculas entre sistemas operativos, omisiones de traducción y colisiones de variables críticas **antes de compilar o publicar el juego**.

---

## 1. Principios de Arquitectura y Seguridad

* **100% Estático y Seguro**: Trata el código del juego analizado como **datos no confiables**. Jamás ejecuta `eval()`, `exec()`, `compile()`, ni importa scripts `.rpy` o módulos de Python del usuario.
* **Cero Modificación de Archivos**: Opera bajo el principio estricto de solo lectura (`SCAN → ANALYZE → REPORT`). No altera ni reescribe ningún archivo del proyecto del usuario.
* **Totalmente Local y Offline**: No requiere conexión a internet ni telemetría. La totalidad del código, assets y metadatos se procesa localmente en la máquina del desarrollador.
* **Alta Precisión y Desempeño**: Parser determinista sin dependencias externas pesadas, capaz de analizar proyectos completos con cientos de scripts y miles de assets en menos de 1 segundo.

---

## 2. Características Principales

1. **Interfaz Gráfica de Escritorio (PySide6 / Qt6)**:
   * Tema oscuro moderno diseñado para desarrolladores (inspirado en Linear y VS Code).
   * Selector con soporte para **Drag & Drop** de carpetas de proyectos Ren'Py.
   * Tarjetas métricas interactivas con conteos en tiempo real por severidad (Total, Errors, Warnings, Info).
   * Barra de filtrado dinámico en tiempo real (búsqueda textual instantánea, filtro por severidad y filtro por categoría).
   * Tabla interactiva de incidencias con badges de color y visualización de rutas relativas y números de línea.
   * Panel lateral de diagnóstico detallado con formateador de snippets de código fuente en bloque monoespaciado y **recomendaciones de corrección accionables**.
   * Hilo de análisis en segundo plano (`QThread`) para mantener la interfaz 100% fluida durante el escaneo.

2. **Herramienta CLI para Pipelines e Integración Continua (CI/CD)**:
   * Salida enriquecida en terminal con resumen de estadísticas y desglose de problemas.
   * Códigos de salida estándar para fallar automáticamente builds de CI ante errores críticos.
   * Flags `--export-json` y `--export-html` para automatización sin interfaz gráfica.

3. **Motor de Reportes Multi-Formato**:
   * **Reporte HTML Interactivo Autónomo**: Archivo HTML único y autocontenido (zero CDN, CSS/JS integrados) con buscador interactivo, filtros de severidad y diseño responsivo para compartir con directores y traductores.
   * **Reporte JSON Estructurado**: Esquema versionado v1.0.0 listo para ingesta en sistemas de QA, SonarQube o dashboards web.

4. **Arquitectura de Niveles Comerciales (Tiers)**:
   * **Free Edition**: Análisis esencial de flujo (jumps, calls, labels duplicadas, assets de audio e imagen).
   * **Pro Edition**: Reglas avanzadas de traducción, discrepancias entre sistemas operativos (Linux/Steam Deck), activos huérfanos, reportes interactivos HTML y exportación JSON para equipos de desarrollo.
   * **Developer Edition**: Sistema de plugins para cargar reglas personalizadas in-house desde archivos `.py` externos.

5. **Empaquetado Standalone para Windows**:
   * Especificación PyInstaller optimizada (`renpy_inspector.spec`) y scripts de compilación listos para generar el ejecutable `.exe` sin requerir Python en la máquina destino.

---

## 3. Catálogo Completo de Reglas de QA

Ren'Py Inspector incluye **14 reglas estáticas deterministas**:

| ID | Regla | Severidad | Categoría | Edición | Descripción |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RPY-CODE-001` | **Broken Jump Target** | `ERROR` | Code | Free | Detecta sentencias `jump` que apuntan a labels inexistentes. |
| `RPY-CODE-002` | **Broken Call Target** | `ERROR` | Code | Free | Detecta sentencias `call` hacia labels que no están definidas. |
| `RPY-CODE-003` | **Duplicate Label** | `ERROR` | Code | Free | Identifica colisiones donde un mismo label se define en múltiples archivos. |
| `RPY-CODE-004` | **Conflicting Define/Default** | `WARNING` | Code | Free | Alerta cuando una variable se declara simultáneamente con `define` y `default`. |
| `RPY-CODE-005` | **Unused Label** | `INFO` | Code | Pro | Detecta labels que nunca son alcanzados por jumps, calls ni referencias de menú. |
| `RPY-CODE-006` | **Shadowed Ren'Py Builtin** | `WARNING` | Code | Pro | Detecta variables que sobreescriben objetos reservados del motor (`renpy`, `config`, `store`). |
| `RPY-SCREEN-001` | **Undefined Screen** | `ERROR` | Code | Pro | Detecta invocaciones `call screen` hacia pantallas que no existen en el proyecto. |
| `RPY-ASSET-001` | **Missing Image File** | `ERROR` | Assets | Free | Detecta imágenes declaradas en sentencias `image` que no existen en disco. |
| `RPY-ASSET-002` | **Missing Audio File** | `ERROR` | Assets | Free | Detecta pistas de música, sonido o voz invocadas con `play`/`queue` que faltan. |
| `RPY-ASSET-003` | **Missing Font File** | `ERROR` | Assets | Free | Detecta fuentes tipográficas configuradas en variables `gui.*` o script ausentes en `game/`. |
| `RPY-ASSET-004` | **Case Mismatch** | `WARNING` | Assets | Pro | Detecta diferencias de mayúsculas/minúsculas para prevenir crashes en Linux/Steam Deck. |
| `RPY-ASSET-005` | **Unused Asset Candidate** | `INFO` | Assets | Pro | Detecta imágenes y audios en disco que no tienen ninguna referencia en el script. |
| `RPY-AUDIO-002` | **Invalid Audio Channel** | `WARNING` | Assets | Pro | Detecta typos o canales de audio no estándar en sentencias de reproducción. |
| `RPY-TRANS-001` | **Missing Translation Block** | `WARNING` | Translation | Pro | Alerta sobre bloques de diálogo traducidos en un idioma pero faltantes en otros. |

---

## 4. Instalación y Uso

### Requisitos del Sistema
* Windows 10/11, macOS 12+, o Linux x86_64.
* Python 3.11 o superior.
* PySide6 (incluido en las dependencias).

### Instalación en Modo Desarrollador
```bash
# Clonar o situarse en la carpeta del proyecto
cd renpy_inspector

# Instalar en modo editable con herramientas de desarrollo
pip install -e ".[dev]"
```

---

## 5. Guía Rápida de Uso

### Modo Gráfico (GUI)
Para iniciar la interfaz de usuario:
```bash
# Lanzar la aplicación gráfica directamente
renpy-inspector-gui

# O abrir un proyecto específico directamente en la GUI
python -m renpy_inspector --gui "C:/Juegos/MiProyectoRenpy"
```

### Modo Línea de Comandos (CLI)
```bash
# Inspección básica por terminal
python -m renpy_inspector "C:/Juegos/MiProyectoRenpy"

# Mostrar también avisos informativos (como assets no utilizados)
python -m renpy_inspector "C:/Juegos/MiProyectoRenpy" --show-info

# Exportar reportes automatizados en formato HTML interactivo y JSON
python -m renpy_inspector "C:/Juegos/MiProyectoRenpy" --export-html report.html --export-json report.json
```

---

## 6. Compilación Standalone para Windows (.exe)

Para compilar un ejecutable independiente de Windows que no requiera Python preinstalado:

```powershell
# Opción 1: Ejecutar el script PowerShell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1

# Opción 2: Ejecutar el script Python directo
python scripts/build_windows.py
```

El ejecutable optimizado se generará en la carpeta `dist/RenPyInspector.exe`.

---

## 7. Ejecución de Tests y Auditoría de Calidad

El proyecto cuenta con una cobertura de pruebas automatizadas superior al **91%** con cero errores de linter:

```bash
# Ejecutar la suite completa de pruebas
pytest

# Ejecutar pruebas con reporte de cobertura detallado
pytest --cov=renpy_inspector

# Validar estilo de código con ruff
ruff check .
```
