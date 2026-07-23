# Repo Analyzer

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Repo Analyzer** es una herramienta CLI en Python que analiza un repositorio de código y genera un **evidence pack** estandarizado: métricas, dependencias, seguridad, calidad, historial, documentación generada con IA y un **score de madurez de ingeniería (0-100)**, listo para due diligence de VC, compliance o auditorías técnicas.

## 🚀 Características

### 🔍 Detección Multi-Stack
- **Node.js**: NestJS, Express, React, Next.js, Vue, Angular
- **React**: ReactJS, ReactJS + TypeScript, React Native
- **Python**: Django, FastAPI, Flask
- **Package Managers**: npm, yarn, pnpm, pip, pipenv, poetry

### 📊 Análisis Completo
- **Métricas de código**: líneas de código, archivos, desglose por lenguaje
- **Dependencias**: parseo completo de dependencias y lockfiles
- **Seguridad**: SAST (Snyk Code) y SCA (npm audit, safety, pip-audit)
- **Calidad**: ejecución automática de tests y recolección de cobertura
- **Historial**: extracción de commits, tags y generación de changelog

### 🎯 VC-Ready Engineering Score
- Calcula un score de **0 a 100** ponderando 7 dimensiones: *velocity, stability, scalability, security, maintainability, bus factor* y *governance*.
- Los pesos y las métricas de cada dimensión se definen en [`metrica.json`](metrica.json) — ajustables sin tocar código.
- Resultado guardado en `score.json` dentro del evidence pack.

### 🤖 Documentación con IA
- **Diagramas C4**: Context y Container en Mermaid
- **Diagramas de secuencia**: PlantUML con renderizado automático
- **Documentación**: README enriquecido, Runbook y Architecture docs generados con OpenAI o Gemini
- **Multi-idioma**: español, inglés, francés, alemán y más
- **Cache local**: evita regenerar contenido de IA entre corridas (desactivable con `--no-cache`)

### ☁️ Integración Cloud
- **Upload automático** del evidence pack a plataformas externas
- **Métodos**: ZIP (recomendado) o archivos individuales
- **Autenticación**: Bearer, SAS o header custom

## 🏗️ Arquitectura

`cli.py` orquesta un pipeline de módulos independientes. Cada módulo recibe la ruta del repo (y, en algunos casos, la salida del paso anterior) y devuelve datos estructurados; `EvidenceGenerator` junta todo y escribe el evidence pack en disco.

```
                         ┌────────────────────┐
                         │   repo_analyzer.py  │  ← entry point
                         │   (cli.py: main)     │
                         └──────────┬──────────┘
                                    │
   1. StackDetector ────────────────┤  detecta lenguaje, frameworks, package manager
   2. DependencyParser ─────────────┤  parsea dependencias y lockfiles
   3. RepoFactsCollector ───────────┤  metadata de git (nombre, commit, remoto)
   4. SecurityAnalyzer ─────────────┤  SAST (Snyk) + SCA (npm audit / safety / pip-audit)
   5. QualityAnalyzer ──────────────┤  corre tests y recolecta cobertura
   6. MetricsCollector ─────────────┤  LOC y desglose por lenguaje
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   EvidenceGenerator    │  orquesta el resto y escribe /out
                         └──────────┬───────────┘
                        ┌───────────┼───────────────┐
                        ▼           ▼               ▼
                 AIDocGenerator  ScoringSystem   EvidenceUploader
                 (docs + diagramas   (score.json      (opcional, sube
                  vía OpenAI/Gemini,  vía metrica.json) el evidence pack)
                  con CacheManager)
```

### Módulos (`repo_analyzer/`)

| Módulo | Responsabilidad |
|--------|------------------|
| `cli.py` | Punto de entrada CLI (Click). Orquesta el pipeline paso a paso. |
| `stack_detector.py` | Detecta lenguaje principal, frameworks, package manager, TypeScript, mobile. |
| `dependency_parser.py` | Parsea `package.json`, `requirements.txt`, lockfiles, etc. |
| `repo_facts.py` | Extrae metadata del repo vía git (nombre, commit SHA, remoto, tags). |
| `security_analyzer.py` | SAST con Snyk Code (requiere `SNYK_TOKEN`) y SCA con npm audit / safety / pip-audit. |
| `quality_analyzer.py` | Detecta el framework de testing, corre la suite y recolecta cobertura. |
| `metrics_collector.py` | Cuenta líneas de código y arma el desglose por lenguaje. |
| `evidence_generator.py` | Arma el evidence pack completo (JSON, docs, diagramas, checksums). |
| `ai_doc_generator.py` | Genera docs (README/runbook/architecture) y diagramas C4/secuencia vía OpenAI o Gemini. |
| `scoring_system.py` | Calcula el VC-Ready Engineering Score a partir de `metrica.json`. |
| `cache_manager.py` | Cachea en disco las respuestas de IA para no regenerarlas en cada corrida. |
| `uploader.py` | Sube el evidence pack (zip o archivo por archivo) a una plataforma externa. |

## 📦 Instalación

### Requisitos
- Python 3.8 o superior
- Git (para análisis de historial y metadata del repo)

### Instalación Básica

```bash
# Clonar el repositorio
git clone https://github.com/emanriquez/code-analyzer.git
cd code-analyzer

# Opción 1: Instalar como paquete editable (recomendado)
pip install -e .

# Opción 2: Instalar solo las dependencias desde requirements.txt
pip install -r requirements.txt
```

Ambas opciones exponen el comando `repo-analyzer` (vía entry point) y el script `repo_analyzer.py` en la raíz del proyecto — puedes usar cualquiera de los dos indistintamente.

### Instalación con Dependencias de IA

`openai` y `google-generativeai` se instalan automáticamente con `pip install -e .`. Si solo necesitas uno de los dos proveedores:

```bash
# Solo OpenAI
pip install openai

# Solo Gemini
pip install google-generativeai
```

## 🎯 Uso Básico

### Análisis Simple

```bash
python repo_analyzer.py --repo /path/to/repo --out ./evidence
```

### Con Análisis de Seguridad

El token de Snyk **no** tiene valor por defecto — debes pasarlo explícitamente o vía variable de entorno:

```bash
export SNYK_TOKEN=tu-snyk-token   # o pásalo con --snyk-token

python repo_analyzer.py \
  --repo /path/to/repo \
  --out ./evidence \
  --snyk-token $SNYK_TOKEN
```

### Con Generación de Documentación IA

```bash
python repo_analyzer.py \
  --repo /path/to/repo \
  --out ./evidence \
  --openai-token sk-... \
  --language es
```

### Upload a Plataforma Externa

```bash
python repo_analyzer.py \
  --repo /path/to/repo \
  --out ./evidence \
  --upload-url https://api.compliance-platform.com \
  --upload-token tu-token \
  --upload-method zip
```

## 📖 Ejemplos Completos

### Ejemplo 1: Análisis Completo con IA

```bash
python repo_analyzer.py \
  --repo . \
  --out ./evidence \
  --snyk-token $SNYK_TOKEN \
  --openai-token $OPENAI_API_KEY \
  --language es \
  --verbose
```

### Ejemplo 2: Con Upload Automático

```bash
python repo_analyzer.py \
  --repo . \
  --out ./evidence \
  --repo-name my-repo \
  --commit-sha abc123 \
  --snyk-token $SNYK_TOKEN \
  --openai-token $OPENAI_API_KEY \
  --upload-url https://api.platform.com \
  --upload-token $UPLOAD_TOKEN \
  --upload-method zip \
  --upload-auth-type bearer \
  --verbose
```

### Ejemplo 3: Usando Gemini en lugar de OpenAI

```bash
python repo_analyzer.py \
  --repo . \
  --out ./evidence \
  --gemini-token $GEMINI_API_KEY \
  --ai-provider gemini \
  --language es
```

## 📁 Estructura del Evidence Pack

El analyzer genera un evidence pack con la siguiente estructura:

```
evidence/
├── summary.json                    # Resumen ejecutivo
├── dependencies.json               # Dependencias parseadas
├── repo_facts.json                 # Metadatos del repositorio
├── score.json                      # VC-Ready Engineering Score (según metrica.json)
├── SHA256SUMS                      # Checksums de integridad
│
├── metrics/
│   ├── cloc.json                   # Métricas de código
│   └── languages.json              # Desglose por lenguajes
│
├── quality/
│   ├── tests.json                  # Resultados de tests
│   └── coverage-summary.json       # Cobertura de código
│
├── security/
│   └── deps-sca.json               # Análisis de vulnerabilidades
│
├── change/
│   ├── commits.json                # Historial de commits
│   └── changelog.md                # Changelog en Markdown
│
├── docs/
│   ├── README.enriched.md          # README generado con IA
│   ├── runbook.md                  # Runbook operacional
│   └── architecture.md             # Documentación de arquitectura
│
├── diagrams/
│   ├── c4_context.mmd              # Diagrama C4 Context
│   ├── c4_container.mmd            # Diagrama C4 Container
│   ├── sequence.puml                # Diagrama de secuencia
│   └── sequence.png                # (Opcional) Imagen renderizada
│
└── build/
    └── build.json                  # Información del build
```

## 🔧 Opciones de Línea de Comandos

### Opciones Principales

| Opción | Descripción | Requerido |
|--------|-------------|-----------|
| `--repo`, `-r` | Ruta al repositorio a analizar | No (default: `.`) |
| `--out`, `-o` | Directorio de salida | No (default: `./out`) |
| `--verbose`, `-v` | Modo verbose | No |

### Análisis

| Opción | Descripción |
|--------|-------------|
| `--repo-name` | Nombre del repositorio |
| `--commit-sha` | SHA del commit |
| `--build-id` | ID del build |

### Seguridad

| Opción | Descripción |
|--------|-------------|
| `--snyk-token` | Token de Snyk para análisis de código (sin default, usar env var o flag) |

### IA y Documentación

| Opción | Descripción |
|--------|-------------|
| `--openai-token` | Token de OpenAI API |
| `--gemini-token` | Token de Google Gemini API |
| `--ai-provider` | Proveedor: `openai`, `gemini`, `auto` |
| `--language`, `--lang` | Idioma: `en`, `es`, `fr`, `de`, etc. |
| `--no-cache` | Deshabilitar cache de IA |

### Upload

| Opción | Descripción |
|--------|-------------|
| `--upload-url` | URL base para upload |
| `--upload-token` | Token de autenticación |
| `--upload-method` | Método: `zip` o `individual` |
| `--upload-auth-type` | Tipo: `bearer`, `sas`, `custom` |
| `--upload-custom-header` | Header personalizado (si auth-type es custom) |

## 🌐 Variables de Entorno

Puedes usar variables de entorno en lugar de parámetros:

```bash
export SNYK_TOKEN=tu-token
export OPENAI_API_KEY=sk-...
export EVIDENCE_UPLOAD_URL=https://api.platform.com
export EVIDENCE_UPLOAD_TOKEN=tu-token

python repo_analyzer.py --repo . --out ./evidence
```

## 🎯 VC-Ready Engineering Score

`metrica.json` define el modelo de scoring: 7 dimensiones (`velocity`, `stability`, `scalability`, `security`, `maintainability`, `bus_factor`, `governance`), cada una con su propio peso y su propia lista de métricas ponderadas. `ScoringSystem` lee ese archivo, cruza las métricas disponibles en el evidence pack (tests, cobertura, vulnerabilidades, dependencias, actividad de commits, etc.) y calcula un score final de 0 a 100, guardado en `score.json`.

Puedes ajustar pesos o agregar métricas editando `metrica.json` sin tocar el código de `scoring_system.py`.

## 🔐 Seguridad

- Los tokens nunca se imprimen en logs (solo se muestra "configured" en verbose)
- Los tokens se pasan como variables de entorno o parámetros — **no hay tokens hardcodeados en el código**
- Soporte para múltiples métodos de autenticación
- Checksums SHA256 para verificación de integridad del evidence pack

## 🚀 Integración con CI/CD

### GitHub Actions

```yaml
- name: Generate Evidence Pack
  run: |
    pip install git+https://github.com/emanriquez/code-analyzer.git
    python -m repo_analyzer.cli \
      --repo . \
      --out ./evidence \
      --repo-name ${{ github.repository }} \
      --commit-sha ${{ github.sha }} \
      --snyk-token ${{ secrets.SNYK_TOKEN }} \
      --openai-token ${{ secrets.OPENAI_API_KEY }} \
      --language es \
      --verbose
```

### Azure DevOps

```yaml
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.11'

- script: |
    pip install git+https://github.com/emanriquez/code-analyzer.git
  displayName: 'Install repo-analyzer'

- script: |
    python -m repo_analyzer.cli \
      --repo $(Build.SourcesDirectory) \
      --out $(Build.ArtifactStagingDirectory)/evidence \
      --snyk-token $(SNYK_TOKEN) \
      --openai-token $(OPENAI_API_KEY) \
      --language es \
      --upload-url $(EVIDENCE_UPLOAD_URL) \
      --upload-token $(EVIDENCE_UPLOAD_TOKEN) \
      --verbose
  displayName: 'Generate evidence pack'
```

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT.

## 🙏 Agradecimientos

- OpenAI y Google Gemini por las APIs de IA
- La comunidad de herramientas de análisis estático
- Todos los contribuidores

## 📧 Contacto

Para preguntas o soporte, abre un issue en GitHub.

---

**Hecho con ❤️ para automatizar documentación y compliance**
