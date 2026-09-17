# Ren'Py Inspector — User Guide & Manual de Usuario

Bienvenido a la guía oficial de usuario de **Ren'Py Inspector**.

Este manual explica detalladamente cómo utilizar la herramienta en sus modalidades de interfaz gráfica de escritorio (GUI), ejecutable independiente para Windows (`.exe`) y línea de comandos (CLI), cómo integrarla en flujos automatizados de CI/CD, cómo personalizar su configuración y cómo extenderla con reglas propias.

---

## 1. Modalidades de Ejecución

Ren'Py Inspector puede ejecutarse de tres formas según tu entorno de trabajo:

### 1.1 Ejecutable Standalone de Windows (`RenPyInspector.exe`)
Si dispones de la versión compilada para Windows, no requieres instalar Python ni dependencias externas:
* **Doble clic**: Haz doble clic sobre `RenPyInspector.exe` para abrir la interfaz gráfica de inmediato.
* **Desde PowerShell / CMD**:
  ```powershell
  .\RenPyInspector.exe
  # O abrir un proyecto específico directamente
  .\RenPyInspector.exe "C:\Juegos\MiProyectoRenpy"
  ```

### 1.2 Interfaz Gráfica con Python / PySide6 (GUI)
Si estás usando el entorno virtual de Python:
```bash
# Iniciar la aplicación gráfica directamente
renpy-inspector-gui

# O bien mediante el comando del módulo
python -m renpy_inspector --gui "C:/Juegos/MiProyectoRenpy"
```

### 1.3 Herramienta de Línea de Comandos (CLI)
Ideal para integración continua, terminales de desarrollo y scripts de automatización:
```bash
# Inspección estándar de un proyecto
python -m renpy_inspector "C:/Juegos/MiProyectoRenpy"
```

---

## 2. Guía de la Interfaz Gráfica de Escritorio (Desktop GUI)

### 2.1 Selección y Carga del Proyecto
1. **📁 Botón Browse**: Haz clic para navegar y seleccionar la carpeta raíz de tu juego Ren'Py o directamente la subcarpeta `game/`.
2. **Arrastrar y Soltar (Drag & Drop)**: Arrastra la carpeta de tu juego directamente desde el Explorador de Archivos de Windows o Finder sobre la ventana de la aplicación.
3. **Indicador de Validación**:
   * <span style="color:#3fb950; font-weight:bold;">Verde</span>: Directorio `game/` detectado y válido. Listo para inspeccionar.
   * <span style="color:#e3b341; font-weight:bold;">Amarillo</span>: La carpeta seleccionada no parece contener la estructura estándar de Ren'Py.
4. Haz clic en **🔍 Inspect Project** para iniciar el análisis.

### 2.2 Barra de Progreso y Evaluación Asíncrona
Durante la inspección, la aplicación ejecuta el análisis en un hilo en segundo plano (`QThread`) para mantener la ventana 100% fluida y responsiva:
* La barra de progreso muestra el avance en porcentaje ($0\% \to 100\%$).
* La etiqueta de estado informa en tiempo real qué regla se está evaluando paso a paso (ejemplo: `Evaluando regla 7/20: Unreachable Code Statement...`).

### 2.3 Dashboard de Tarjetas Métricas
Una vez finalizado el análisis (generalmente en menos de 1 segundo), verás:
* **TOTAL ISSUES**: Conteo global de incidencias detectadas.
* **ERRORS / CRITICAL**: Fallos críticos que causarán un crash en tiempo de ejecución o romperán el flujo del juego (ej. saltos hacia labels inexistentes, pantallas no definidas o variables persistentes mal declaradas).
* **WARNINGS**: Discrepancias potenciales que pueden causar comportamientos inesperados (ej. inconsistencias de mayúsculas/minúsculas entre Windows y Linux/Steam Deck, menús vacíos o etiquetas de texto sin cerrar).
* **INFO / TIPS**: Sugerencias de limpieza y optimización (ej. imágenes o audios en disco sin referencias estáticas, o labels huérfanas).
* **SCANNED IN**: Tiempo exacto de procesamiento expresado en segundos.

> **Tip de Productividad**: Haz clic sobre cualquiera de las tarjetas métricas (**TOTAL**, **ERRORS**, **WARNINGS**, **INFO**) para filtrar la tabla al instante con un solo clic.

### 2.4 Filtrado y Búsqueda Multi-Criterio
La barra superior de filtrado permite combinar criterios dinámicos en tiempo real:
* **Buscador de Texto**: Escribe cualquier término (ej. `script.rpy`, `RPY-CODE-001`, `screen`, `menu`) para filtrar inmediatamente la tabla mientras escribes.
* **Selector de Severidad**: Filtra por `All Severities`, `CRITICAL`, `ERROR`, `WARNING` o `INFO`.
* **Selector de Categoría**: Filtra por categorías especializadas:
  * `Code`: Lógica, saltos, menús, etiquetas, código inalcanzable y persistencia.
  * `Assets`: Fuentes tipográficas, canales de audio y archivos huérfanos.
  * `Audio`: Pistas de música, sonido y voz faltantes.
  * `Images`: Declaraciones de imágenes ausentes en disco.
  * `Translation`: Bloques de localización y traducciones incompletas.
  * `References`: Discrepancias de mayúsculas/minúsculas entre código y sistema de archivos.
* **Reset Filters**: Restablece todos los filtros para mostrar la totalidad de incidencias.

### 2.5 Panel de Diagnóstico Detallado
Al seleccionar una fila en la tabla de incidencias, el panel derecho muestra:
1. **Badge de Severidad e ID de Regla**: Identificador canónico (ej. `RPY-CODE-008`).
2. **Título del Problema**: Descripción concisa del fallo.
3. **Ubicación en Disco**: Ruta relativa (`game/script.rpy:L45`) para fácil localización.
4. **Descripción del Error**: Explicación técnica de la causa del fallo y su impacto en Ren'Py.
5. **Visor de Código Fuente**: Fragmento de código extraído automáticamente con el error contextualizado en tipografía monoespaciada.
6. **Acción Recomendada (`💡 RECOMMENDED ACTION`)**: Instrucción precisa de cómo editar el archivo para solucionar el problema.

### 2.6 Exportación de Reportes
En la esquina superior derecha, dispones de dos botones de exportación:
* **Export HTML**: Genera un reporte interactivo en un único archivo `.html` (100% autocontenido, zero dependencias externas). Incluye su propio buscador en JavaScript, tarjetas métricas y diseño responsivo para compartir con directores, guionistas o traductores.
* **Export JSON**: Genera un archivo estructurado `.json` v1.0.0 listo para ingesta en sistemas de QA corporativos, dashboards o scripts personalizados.

---

## 3. Uso desde la Línea de Comandos (CLI)

Ren'Py Inspector cuenta con una interfaz CLI robusta para terminales (PowerShell, Bash, Zsh) y scripts de automatización:

### Comandos Frecuentes
```bash
# Inspección estándar de un proyecto
python -m renpy_inspector "C:/Juegos/MiProyectoRenpy"

# Mostrar incidencias de nivel INFO (assets sin uso en disco, etc.)
python -m renpy_inspector "C:/Juegos/MiProyectoRenpy" --show-info

# Generar ambos reportes de forma desatendida
python -m renpy_inspector "C:/Juegos/MiProyectoRenpy" --export-html "reports/qa.html" --export-json "reports/qa.json"
```

### Códigos de Salida (Exit Codes para CI/CD)
* `0`: El proyecto está limpio y no contiene errores de severidad `ERROR` ni `CRITICAL`.
* `1`: El proyecto contiene uno o más errores críticos, o la ruta especificada no es un proyecto Ren'Py válido.

---

## 4. Catálogo de Reglas Disponibles (20 Reglas Estáticas)

| Código | Nombre | Severidad | Categoría |
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

## 5. Configuración Personalizada (`renpy-inspector.toml`)

Puedes personalizar las reglas y el comportamiento del análisis creando un archivo `renpy-inspector.toml` en la raíz de tu juego (o configurando la sección `[tool.renpy-inspector]` en tu `pyproject.toml`):

```toml
[tool.renpy-inspector]
# Desactivar reglas que no apliquen a tu proyecto
disabled_rules = [
    "RPY-ASSET-001",  # Omitir aviso de assets no referenciados
]

# Excluir rutas específicas (ej. plantillas o cachés)
ignore_patterns = [
    "game/tl/None/**",
    "game/cache/**",
]

# Registrar canales de audio personalizados de tu juego
custom_audio_channels = [
    "ambient",
    "sfx_loop",
]

# Sobrescribir la severidad por defecto de ciertas reglas
[tool.renpy-inspector.severity_overrides]
"RPY-CODE-007" = "ERROR"   # Elevar código inalcanzable a error crítico
```

---

## 6. Integración en CI/CD (GitHub Actions)

Para auditar automáticamente cada commit o Pull Request antes de compilar tu juego, crea el archivo `.github/workflows/renpy_inspector.yml`:

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

## 7. Compilación del Ejecutable Standalone para Windows

Si deseas compilar tu propio binario `.exe` independiente de Ren'Py Inspector:

```powershell
# Compilación con script PowerShell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1

# O compilación directa con Python
python scripts/build_windows.py
```

El binario autocontenido se generará en `dist/RenPyInspector.exe`.

---

## 8. Edición para Desarrolladores: Creación de Reglas Personalizadas

En la **Developer Edition**, puedes añadir reglas in-house adaptadas a la arquitectura de tu estudio creando archivos `.py` en una carpeta de plugins:

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

El cargador dinámico de plugins registrará la clase e integrará la regla en el ciclo de escaneo tanto en la CLI como en la interfaz gráfica.
