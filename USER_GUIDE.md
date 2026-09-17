# Ren'Py Inspector — User Guide & Manual de Usuario

Bienvenido a la guía oficial de usuario de **Ren'Py Inspector**.

Este manual explica detalladamente cómo utilizar la herramienta en sus modalidades de interfaz de escritorio (GUI) y línea de comandos (CLI), cómo integrarla en flujos automatizados de CI/CD, y cómo escribir reglas personalizadas.

---

## 1. Primeros Pasos con la Interfaz Gráfica (Desktop GUI)

### 1.1 Iniciar la aplicación
Para iniciar la aplicación, ejecuta desde la consola:

```bash
renpy-inspector-gui
```

O bien:

```bash
python -m renpy_inspector --gui
```

### 1.2 Seleccionar o Arrastrar un Proyecto
1. Puedes hacer clic en el botón **📁 Browse...** y seleccionar la carpeta raíz de tu juego Ren'Py (la carpeta que contiene el directorio `game/`).
2. También puedes **arrastrar y soltar (Drag & Drop)** la carpeta de tu juego directamente sobre la ventana de Ren'Py Inspector.
3. El indicador de estado verificará que la carpeta contiene un directorio `game/` válido.
4. Haz clic en el botón **🔍 Inspect Project**.

### 1.3 Lectura del Dashboard y Tarjetas Métricas
Una vez finalizado el análisis (generalmente en menos de 1 segundo), verás:

* **TOTAL ISSUES**: Número global de advertencias, errores e incidencias detectadas.
* **ERRORS / CRITICAL**: Problemas graves que causarán un crash inmediato en tiempo de ejecución (ej. un `jump` hacia un label inexistente o una pantalla llamada con `call screen` no definida).
* **WARNINGS**: Problemas potenciales o de consistencia (ej. diferencias de mayúsculas/minúsculas entre Windows y Linux/Steam Deck, variables con `define` y `default` simultáneos, o traducciones incompletas).
* **INFO / TIPS**: Sugerencias de optimización (ej. assets no utilizados en disco o labels huérfanos).
* **SCANNED IN**: Tiempo exacto que tomó el análisis.

> **Tip**: Puedes hacer clic en cualquiera de las tarjetas (como **ERRORS** o **WARNINGS**) para filtrar instantáneamente la tabla y ver solo los problemas de esa severidad.

### 1.4 Filtrado y Búsqueda en Tiempo Real
La barra de filtros permite acotar los resultados:
* **Buscador de texto**: Escribe cualquier término (ej. el nombre de un archivo `script.rpy`, un nombre de label `chapter2`, o el ID de una regla `RPY-CODE-001`) para filtrar los resultados al instante mientras escribes.
* **Desplegable de Severidad**: Filtra por `CRITICAL`, `ERROR`, `WARNING` o `INFO`.
* **Desplegable de Categoría**: Filtra por `Code`, `Assets` o `Translation`.
* **Reset Filters**: Restaura la visualización completa.

### 1.5 Panel de Diagnóstico Detallado
Al seleccionar cualquier incidencia en la tabla, el panel derecho mostrará:
1. **Identificador de regla y título**: Nombre canónico del problema.
2. **Ubicación exacta**: Archivo y línea de código fuente donde ocurre la discrepancia.
3. **Descripción detallada**: Explicación técnica de por qué Ren'Py fallará o tendrá comportamientos inesperados.
4. **Snippet de código fuente**: Vista del código original con tipografía monoespaciada para contextualizar el error sin abrir un editor de texto.
5. **Acción recomendada**: Sugerencia concreta y lista para aplicar para resolver el problema.

### 1.6 Exportar Reportes (HTML y JSON)
En la esquina superior derecha, encontrarás dos botones:
* **Export HTML**: Genera un reporte interactivo en un único archivo `.html` (autónomo, sin dependencias de internet). Puedes enviarlo a directores de arte, traductores o miembros del equipo que no tengan Ren'Py Inspector instalado.
* **Export JSON**: Genera un archivo `.json` estructurado (versión 1.0.0) ideal para dashboards web o pipelines internos.

---

## 2. Uso desde la Línea de Comandos (CLI)

Ren'Py Inspector es una herramienta nativa para terminales, ideal para scripters que prefieren atajos o scripts en PowerShell / Bash:

### Comandos frecuentes:
```bash
# Inspección estándar de un proyecto
python -m renpy_inspector "C:/Juegos/MiNovelaVisual"

# Incluir sugerencias de nivel INFO (assets no utilizados, etc.)
python -m renpy_inspector "C:/Juegos/MiNovelaVisual" --show-info

# Generar ambos reportes de forma silenciosa
python -m renpy_inspector "C:/Juegos/MiNovelaVisual" --export-html "reports/qa.html" --export-json "reports/qa.json"
```

### Códigos de salida (Exit codes):
* `0`: El proyecto es válido y no contiene errores (`ERROR` o `CRITICAL`).
* `1`: El proyecto contiene uno o más errores de severidad `ERROR` o `CRITICAL`, o la ruta indicada no es un proyecto Ren'Py válido.

---

## 3. Integración en CI/CD (GitHub Actions)

Puedes ejecutar Ren'Py Inspector automáticamente en cada Pull Request o Commit a tu repositorio para evitar que se introduzcan saltos rotos o assets faltantes.

Crea el archivo `.github/workflows/renpy_inspector.yml`:

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
        python -m renpy_inspector . --export-html qa_report.html --export-json qa_report.json

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

## 4. Edición para Desarrolladores: Creación de Reglas Personalizadas

En la **Developer Edition**, puedes añadir tus propias reglas de análisis estático sin modificar el código base de Ren'Py Inspector.

### Cómo crear un plugin de regla
Crea una carpeta `plugins/` en tu entorno y añade un archivo Python (ej. `my_studio_rule.py`):

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
    description = "Verifica que el juego defina el volumen por defecto en preferences.rpy."

    def analyze(self, context) -> list[Issue]:
        issues = []
        has_volume_config = any(
            v.name == "config.default_music_volume" for v in context.all_variables
        )
        if not has_volume_config:
            loc = Location(file_path="game/options.rpy", line_number=1)
            issues.append(
                self.create_issue(
                    message="Variable 'config.default_music_volume' no está definida.",
                    location=loc,
                    suggestion="Añade 'define config.default_music_volume = 0.8' en options.rpy.",
                )
            )
        return issues
```

El cargador de plugins (`PluginLoader`) descubrirá automáticamente la clase e integrará la regla en el ciclo de escaneo.
