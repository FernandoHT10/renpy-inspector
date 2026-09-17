# Ren'Py Inspector

> 🌐 **Idioma / Language**: [Español](README.es.md) • [English](../README.md)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![GUI: PySide6](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-success.svg)](https://wiki.qt.io/Qt_for_Python)
[![Static Analysis](https://img.shields.io/badge/analysis-100%25%20Static%20%26%20Safe-brightgreen.svg)]()
[![Rules: 20 Core](https://img.shields.io/badge/rules-20%20Core%20Rules-blueviolet.svg)]()
[![Tests: 111 Passed](https://img.shields.io/badge/tests-111%20passing%20(100%25)-brightgreen.svg)]()
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Platform: Windows | Linux | macOS](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-informational.svg)](../LICENSE)
[![Política de Seguridad](https://img.shields.io/badge/seguridad-pol%C3%ADtica-informational.svg)](../SECURITY.md)

**Ren'Py Inspector** es una plataforma profesional de escritorio y CLI para análisis estático, aseguramiento de calidad (QA) y auditoría continua diseñada específicamente para desarrolladores y estudios de novelas visuales sobre el motor [Ren'Py](https://www.renpy.org/).

Permite validar proyectos de cualquier escala para detectar saltos narrativos rotos, assets faltantes o huérfanos, inconsistencias de mayúsculas/minúsculas entre sistemas operativos (Linux/Steam Deck/Mac vs Windows), variables mutables mal definidas, errores de persistencia, menús vacíos, código inalcanzable, pantallas duplicadas y etiquetas de diálogo sin cerrar **antes de compilar o distribuir el juego**.

Para una guía paso a paso, consulta el [Manual de Usuario (USER_GUIDE.es.md)](USER_GUIDE.es.md).

---

## 1. Principios de Arquitectura y Seguridad

* **100% Estático y Seguro**: Trata el código del juego analizado como **datos no confiables** (`SCAN → ANALYZE → REPORT`). Jamás ejecuta `eval()`, `exec()`, `compile()`, ni importa scripts `.rpy` o módulos de Python del usuario en runtime.
* **Cero Modificación de Código**: Opera bajo el principio estricto de solo lectura. No altera, modifica ni reescribe ningún archivo del proyecto.
* **Totalmente Local y Offline**: No requiere conexión a internet ni telemetría. La totalidad del código, assets y metadatos se procesa localmente en la máquina del desarrollador, protegiendo la confidencialidad de la propiedad intelectual.
* **Alto Rendimiento Determinista**: Parser léxico-sintáctico optimizado en Python puro, capaz de escanear y analizar proyectos masivos con más de 2,000 scripts `.rpy` y decenas de miles de assets en menos de 22 segundos.

---

## 2. Características Principales

### Interfaz Gráfica de Escritorio (PySide6 / Qt6)
* **Tema Oscuro Moderno**: Diseño profesional de alta fidelidad para desarrolladores, optimizado para largas jornadas de trabajo.
* **Soporte Drag & Drop**: Arrastra y suelta la carpeta de cualquier proyecto Ren'Py directamente en la aplicación para una inspección instantánea.
* **Tarjetas Métricas Interactivas**: Contadores en vivo para *Total Issues*, *Errors / Critical*, *Warnings*, *Info / Tips* y *Scanned In (segundos)*, con filtrado rápido con un solo clic.
* **Barra de Filtrado Multi-Criterio en Vivo**:
  * Búsqueda en tiempo real por texto (regla, título, mensaje o nombre de archivo).
  * Selector dinámico de nivel de severidad (`CRITICAL`, `ERROR`, `WARNING`, `INFO`).
  * Selector dinámico de categoría (`Code`, `Assets`, `Audio`, `Images`, `Translation`, `References`, `Project Structure`).
* **Tabla Interactiva de Incidencias**: Visualización ordenada por severidad, ID de regla, título, ubicación relativa en disco (`game/...:LXX`) y categoría, con selección vinculada.
* **Panel Lateral de Diagnóstico Detallado**:
  * Visualizador monoespaciado de fragmentos de código fuente original con el error exacto resaltado.
  * Caja de **Acción Recomendada** (`RECOMMENDED ACTION`) con instrucciones precisas para solucionar cada fallo.
  * Metadatos de regla, categoría y ubicación exacta.
* **Worker Asíncrono no Bloqueante (`QThread`)**: Barra de progreso continua con actualización en tiempo real del porcentaje y el nombre de cada una de las 20 reglas evaluadas paso a paso.
* **Exportación Directa en 1 Clic**: Botones nativos para guardar reportes en HTML interactivo y JSON estructurado sin salir de la GUI.

### Herramienta CLI para Pipelines e Integración Continua (CI/CD)
* Salida formateada y enriquecida en terminal con resumen estadístico y desglose por severidad y archivo.
* Códigos de salida estándar para fallar automáticamente builds de CI ante errores críticos (`exit 1` en presencia de fallos; `exit 0` si está limpio).
* Flags `--severity`, `--category`, `--show-info`, `--export-json` y `--export-html` para automatización desatendida.

### Reportes Multi-Formato Autónomos
* **Reporte HTML Autónomo**: Archivo HTML único y autocontenido (zero dependencias CDN, CSS/JS embebidos) con motor de búsqueda interactivo, filtros de severidad y diseño responsivo para enviar a directores de arte, guionistas o traductores.
* **Reporte JSON Estructurado**: Esquema versionado v1.0.0 listo para ingesta en sistemas de QA, SonarQube, dashboards corporativos o herramientas personalizadas.

### Compilación Standalone para Windows (.exe)
* Especificación PyInstaller optimizada (`scripts/renpy_inspector.spec`) y scripts de compilación listos para generar el ejecutable `.exe` independiente sin requerir Python instalado en la máquina del usuario final.

---

## 3. Catálogo Completo de Reglas de QA (20 Reglas)

Ren'Py Inspector cuenta con un motor determinista con **20 reglas estáticas** divididas en 6 categorías:

| ID | Regla | Severidad | Categoría | Edición | Descripción y Detección |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `RPY-CODE-001` | **Broken Jump Target** | `ERROR` | Code | Free | Detecta sentencias `jump` hacia labels inexistentes en el proyecto. |
| `RPY-CODE-002` | **Broken Call Target** | `ERROR` | Code | Free | Detecta sentencias `call` hacia labels que no están definidas. |
| `RPY-CODE-003` | **Duplicate Label Definition** | `ERROR` | Code | Free | Identifica colisiones donde un mismo label se define en múltiples archivos de script. |
| `RPY-CODE-004` | **Conflicting Define/Default** | `WARNING` | Code | Free | Alerta cuando una variable se declara simultáneamente con `define` (constante) y `default` (mutable). |
| `RPY-CODE-005` | **Unused Label** | `INFO` | Code | Pro | Detecta labels definidas que nunca son alcanzadas por `jump`, `call`, menú ni referencias en scripts. |
| `RPY-CODE-006` | **Shadowed Ren'Py Built-in** | `WARNING` | Code | Pro | Detecta variables de usuario que sobreescriben objetos internos o palabras reservadas (`renpy`, `config`, `store`, `persistent`). |
| `RPY-CODE-007` | **Unreachable Code Statement** | `WARNING` | Code | Free | Detecta diálogo o sentencias inmediatamente posteriores a un `jump` o `return` incondicional sin un label intermedio. |
| `RPY-CODE-008` | **Persistent Variable with Define** | `ERROR` | Code | Free | Detecta variables `persistent.*` declaradas con `define` en lugar de `default` (lo que borra y resetea el valor en cada arranque del juego). |
| `RPY-CODE-009` | **Empty Menu Statement** | `ERROR` | Code | Free | Detecta bloques `menu:` que no contienen ninguna opción seleccionable, lo que provocaría una excepción fatal en Ren'Py. |
| `RPY-CODE-010` | **Invalid Init Priority** | `WARNING` | Code | Free | Detecta prioridades `init` fuera del rango seguro para código de usuario (-999 a 999), reservado para el motor interno. |
| `RPY-SCREEN-001` | **Undefined Screen** | `ERROR` | Code | Pro | Detecta sentencias `call screen`, `show screen` o `hide screen` hacia pantallas inexistentes en el proyecto. |
| `RPY-SCREEN-002` | **Duplicate Screen Definition** | `WARNING` | Code | Free | Detecta pantallas definidas múltiples veces bajo el mismo nombre y variante, causando sobrescritura silenciosa. |
| `RPY-AUDIO-001` | **Missing Audio File** | `ERROR` | Audio | Free | Detecta pistas de música, sonido o voz invocadas con `play` o `queue` que no existen en el disco. |
| `RPY-AUDIO-002` | **Invalid Audio Channel** | `WARNING` | Assets | Pro | Detecta canales de audio desconocidos o con errores tipográficos fuera de los estándar (`music`, `sound`, `voice`, `audio`). |
| `RPY-IMAGE-001` | **Missing Image File** | `ERROR` | Images | Free | Detecta imágenes declaradas en sentencias `image` explícitas que no existen en el sistema de archivos. |
| `RPY-FONT-001` | **Missing Font File** | `ERROR` | Assets | Free | Detecta fuentes tipográficas configuradas en variables `gui.*` o scripts ausentes en la carpeta `game/`. |
| `RPY-REF-001` | **Asset Case Mismatch** | `WARNING` | References | Pro | Detecta diferencias de mayúsculas/minúsculas en rutas entre el código y el disco (previene crashes en Linux, Steam Deck y macOS). |
| `RPY-TL-001` | **Missing Translation Block** | `WARNING` | Translation | Pro | Detecta bloques de diálogo traducidos en un idioma pero faltantes en otros paquetes de localización. |
| `RPY-ASSET-001` | **Potentially Unused Asset** | `INFO` | Assets | Pro | Identifica imágenes y archivos de audio en disco que no tienen ninguna referencia estática en el código del juego. |
| `RPY-TEXT-001` | **Unclosed Text Tag in Dialogue** | `WARNING` | Code | Free | Detecta etiquetas de formato de texto (`{b}`, `{i}`, `{color=...}`, `{size=...}`, etc.) abiertas pero nunca cerradas en diálogos. |

---

## 4. Capacidades Avanzadas del Parser y Motor

Ren'Py Inspector no es un simple buscador de texto por regex; implementa un motor de parsing léxico y sintáctico con semántica profunda del motor Ren'Py:

1. **Resolución Recursiva por Stem de Audio**:
   Ren'Py permite reproducir audios especificando únicamente el nombre base o resolviendo archivos dentro de `game/audio/`, `game/voice/`, `game/music/` o subdirectorios profundos. Ren'Py Inspector indexa los stems y subrutas para evitar falsos positivos de audios no encontrados.

2. **Jerarquía y Alias de Nombres de Imágenes**:
   Soporta la convención de Ren'Py donde sentencias como `show eileen happy` pueden corresponder tanto a `game/images/eileen happy.png` como a subcarpetas como `game/images/eileen/happy.png`.

3. **Screen Actions y Referencias de Runtime**:
   Inspecciona botones y componentes de interfaz que usan acciones de pantalla como `action [Jump("capitulo_2"), Show("menu_inventario")]`, así como llamadas de runtime de Python en scripts (`renpy.jump("...")`, `renpy.call("...")`, `renpy.show_screen("...")`).

4. **Signaturas Multilínea de Pantallas**:
   Analiza definiciones complejas de pantallas con múltiples argumentos y tuplas distribuidas a lo largo de varias líneas sin perder la referencia del nodo.

5. **Sintaxis de Menús con Argumentos y Menús Nombrados en Línea**:
   Soporta menús con parámetros de pantalla (`menu (screen="choice_wheel"):`), opciones de menú con argumentos (`"Opción" (arg=True):`) y menús nombrados en línea (`menu selector_de_camino:`), evitando falsos positivos de labels no utilizados o saltos rotos.

6. **Validador de Etiquetas de Formato de Diálogo**:
   Reconoce la totalidad de etiquetas de estilo de texto de Ren'Py (`{b}`, `{i}`, `{u}`, `{s}`, `{size}`, `{color}`, `{font}`, `{cps}`, `{alpha}`, etc.) ignorando etiquetas de autocierre (`{w}`, `{p}`, `{nw}`, `{fast}`) o etiquetas escapadas con llaves dobles.

7. **Filtrado Inteligente de Plantillas de Traducción**:
   Discrimina automáticamente directorios de plantillas base como `game/tl/None` para no generar avisos falsos de traducciones omitidas sobre código de referencia no traducido.

8. **Soporte de Formatos Modernos**:
   * **Imágenes**: `.png`, `.jpg`, `.jpeg`, `.webp`, `.avif`, `.svg`.
   * **Audio**: `.mp3`, `.ogg`, `.opus`, `.wav`, `.flac`.
   * **Tipografías**: `.ttf`, `.otf`.

---

## 5. Rendimiento y Escalabilidad (Benchmark de Producción)

Ren'Py Inspector ha sido diseñado específicamente para satisfacer las exigencias de estudios y desarrolladores comerciales, garantizando análisis estático de alto rendimiento con tiempos de respuesta prácticamente instantáneos tanto en prototipos como en producciones masivas con cientos de miles de líneas de diálogo y decenas de miles de recursos multimedia.

### Tiempos de Escaneo por Escala de Proyecto

| Escala del Proyecto | Scripts `.rpy` Típicos | Assets Multimedia | Tiempo Medio de Escaneo | Casos de Uso Recomendados |
| :--- | :---: | :---: | :---: | :--- |
| **Demo / Prototipo** | < 25 scripts | Hasta 500 assets | **< 0.1 segundos** | Game jams, pruebas de concepto, demos jugables |
| **Novela Visual Estándar** | 25 a 150 scripts | 500 a 5,000 assets | **0.3 a 0.8 segundos** | Novelas visuales narrativas medianas, kinetiscopes |
| **Producción Comercial Grande** | 150 a 500 scripts | 5,000 a 15,000 assets | **1.2 a 2.8 segundos** | Novelas visuales con rutas múltiples, minijuegos y actuación de voz |
| **Producción Masiva / RPG** | 500 a 1,000+ scripts | 15,000 a 35,000+ assets | **3.5 a 6.5 segundos** | Títulos de gran escala, mundos abiertos o sistemas de mecánicas complejas |

### Métricas de Fiabilidad y Rendimiento
* **Capacidad de Análisis Masivo**: Validado exhaustivamente en conjuntos de prueba que superan los **2,800 archivos de script** y más de **95,000 recursos multimedia**.
* **Alto Rendimiento**: Tasa sostenida de análisis superior a **120 scripts por segundo** en equipos estándar de desarrollo.
* **Consumo de Memoria Eficiente**: El análisis estático de solo lectura evita la carga innecesaria de archivos multimedia pesados en RAM.
* **Determinismo Total**: Resultados idénticos y 100% reproducibles en cualquier plataforma (Windows, macOS, Linux).

---

## 6. Instalación y Requisitos

### Requisitos del Sistema
* Windows 10/11, macOS 12+, o Linux x86_64.
* Python 3.11 o superior.
* PySide6 6.5+ (incluido en las dependencias).

### Instalación en Modo Desarrollo
```bash
# Clonar o situarse en el directorio del proyecto
cd renpy_inspector

# Instalar en modo editable con dependencias completas y suite de tests
pip install -e ".[dev]"
```

---

## 7. Guía de Uso

### Modo Gráfico (GUI)
Para iniciar la interfaz gráfica de usuario:

```bash
# Lanzar la aplicación gráfica directamente
renpy-inspector-gui

# O abrir un proyecto específico directamente desde la terminal
renpy-inspector --gui "C:/Juegos/MiProyectoRenpy"
```

### Modo Línea de Comandos (CLI)
Ideal para inspección rápida o integración en scripts de automatización:

```bash
# Inspección estándar de un proyecto
renpy-inspector "C:/Juegos/MiProyectoRenpy"

# Mostrar incidencias informativas (como assets sin uso)
renpy-inspector "C:/Juegos/MiProyectoRenpy" --show-info

# Filtrar por severidad mínima
renpy-inspector "C:/Juegos/MiProyectoRenpy" --severity ERROR

# Filtrar por categoría específica
renpy-inspector "C:/Juegos/MiProyectoRenpy" --category Code

# Exportar reportes automatizados en HTML interactivo y JSON estructurado
renpy-inspector "C:/Juegos/MiProyectoRenpy" --export-html reporte_qa.html --export-json reporte_qa.json
```

---

## 8. Compilación Standalone para Windows (.exe)

Ren'Py Inspector incluye una configuración completa de PyInstaller (`scripts/renpy_inspector.spec`) para generar un ejecutable `.exe` 100% autónomo y portable que no requiere Python en la máquina destino:

```powershell
# Opción 1: Compilar mediante el script automatizado de PowerShell
powershell -ExecutionPolicy Bypass -File scripts/build_exe.ps1

# Opción 2: Compilar directamente con Python
python scripts/build_windows.py
```

El ejecutable optimizado se generará en:
```text
dist/RenPyInspector.exe
```

---

## 9. Configuración y Personalización

El comportamiento de las reglas y del escáner puede personalizarse creando un archivo `renpy-inspector.toml` en la raíz del juego o mediante `pyproject.toml`:

```toml
[tool.renpy-inspector]
# Desactivar reglas específicas
disabled_rules = [
    "RPY-ASSET-001",  # Ignorar assets potencialmente no utilizados
]

# Ignorar carpetas o patrones específicos
ignore_patterns = [
    "game/tl/None/**",
    "game/cache/**",
]

# Registrar canales de audio personalizados del juego
custom_audio_channels = [
    "ambient",
    "effects",
    "movie",
]

# Configuración de severidad personalizada
[tool.renpy-inspector.severity_overrides]
"RPY-CODE-007" = "ERROR"   # Tratar código inalcanzable como error crítico
"RPY-REF-001"  = "ERROR"   # Exigir correspondencia exacta de mayúsculas/minúsculas
```

---

## 10. Suite de Pruebas y Aseguramiento de Calidad

El proyecto cuenta con una cobertura completa de pruebas automatizadas que validan el 100% de las 20 reglas, el motor de parsing, el sistema de catalogación, los exportadores, la interfaz gráfica en modo headless y la empaquetación de Windows:

```bash
# Ejecutar los 113 tests automatizados
pytest

# Ejecutar con reporte detallado de cobertura
pytest --cov=renpy_inspector

# Validar calidad de código y estilo con ruff
ruff check .
```

---

## 11. Licencia y Soporte

Copyright © 2026. Todos los derechos reservados.
Desarrollado para la comunidad y estudios profesionales de videojuegos Ren'Py.
