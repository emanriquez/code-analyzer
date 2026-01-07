# Repo Analyzer

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Repo Analyzer** es una herramienta CLI en Python que analiza repositorios de código y genera evidence packs estandarizados para documentación técnica, compliance y due diligence de VC.

## 🚀 Características

### 🔍 Detección Multi-Stack
- **Node.js**: NestJS, Express, React, Next.js, Vue, Angular
- **React**: ReactJS, ReactJS + TypeScript, React Native
- **Python**: Django, FastAPI, Flask
- **Package Managers**: npm, yarn, pnpm, pip, pipenv, poetry

### 📊 Análisis Completo
- **Métricas de código**: Líneas de código, archivos, desglose por lenguajes
- **Dependencias**: Parseo completo de dependencias y lockfiles
- **Seguridad**: Análisis SAST (Snyk Code) y SCA (npm audit, safety, pip-audit)
- **Calidad**: Ejecución automática de tests y recolección de cobertura
- **Historial**: Extracción de commits, tags y generación de changelog

### 🤖 Documentación con IA
- **Diagramas C4**: Context y Container diagrams en Mermaid
- **Diagramas de secuencia**: PlantUML con renderizado automático
- **Documentación**: README, Runbook y Architecture docs generados con OpenAI o Gemini
- **Multi-idioma**: Soporte para español, inglés, francés, alemán y más

### ☁️ Integración Cloud
- **Upload automático**: Subida del evidence pack a plataformas externas
- **Métodos**: ZIP (recomendado) o archivos individuales
- **Autenticación**: Bearer, SAS o custom headers

## 📦 Instalación

### Requisitos
- Python 3.8 o superior
- Git (para análisis de historial)

### Instalación Básica

```bash
# Clonar el repositorio
git clone https://github.com/tu-org/repo-analyzer.git
cd repo-analyzer

# Opción 1: Instalar como paquete editable (recomendado)
pip install -e .

# Opción 2: Instalar solo las dependencias desde requirements.txt
pip install -r requirements.txt
```

### Instalación con Dependencias de IA

Las dependencias de OpenAI y Gemini se instalan automáticamente. Si solo necesitas una:

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

```bash
python repo_analyzer.py \
  --repo /path/to/repo \
  --out ./evidence \
  --snyk-token tu-snyk-token
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
├── SHA256SUMS                      # Checksums de integridad
│
├── metrics/
│   ├── cloc.json                   # Métricas de código
│   └── languages.json               # Desglose por lenguajes
│
├── quality/
│   ├── tests.json                   # Resultados de tests
│   └── coverage-summary.json        # Cobertura de código
│
├── security/
│   └── deps-sca.json               # Análisis de vulnerabilidades
│
├── change/
│   ├── commits.json                 # Historial de commits
│   └── changelog.md                 # Changelog en Markdown
│
├── docs/
│   ├── README.enriched.md           # README generado con IA
│   ├── runbook.md                   # Runbook operacional
│   └── architecture.md              # Documentación de arquitectura
│
├── diagrams/
│   ├── c4_context.mmd              # Diagrama C4 Context
│   ├── c4_container.mmd            # Diagrama C4 Container
│   ├── sequence.puml               # Diagrama de secuencia
│   └── sequence.png                # (Opcional) Imagen renderizada
│
└── build/
    └── build.json                   # Información del build
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
| `--snyk-token` | Token de Snyk para análisis de código |

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

## 🏗️ Arquitectura del Módulo

```
repo_analyzer/
├── __init__.py              # Inicialización del módulo
├── cli.py                   # Punto de entrada CLI
├── stack_detector.py        # Detección de tech stack
├── dependency_parser.py     # Parseo de dependencias
├── metrics_collector.py     # Recolección de métricas
├── security_analyzer.py     # Análisis de seguridad
├── quality_analyzer.py      # Análisis de calidad/tests
├── repo_facts.py            # Metadatos del repositorio
├── evidence_generator.py    # Generación del evidence pack
├── ai_doc_generator.py      # Generación con IA
├── cache_manager.py         # Gestión de cache
└── uploader.py              # Upload a plataformas externas
```

## 🔐 Seguridad

- Los tokens nunca se imprimen en logs (solo se muestra "configured" en verbose)
- Los tokens se pasan como variables de entorno o parámetros
- Soporte para múltiples métodos de autenticación
- Checksums SHA256 para verificación de integridad

## 🚀 Integración con CI/CD

### Azure DevOps

Ver [AZURE_DEVOPS_SETUP.md](../AZURE_DEVOPS_SETUP.md) para guía completa.

```yaml
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.11'

- script: |
    pip install git+https://dev.azure.com/org/repo-analyzer/_git/repo-analyzer
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

### GitHub Actions

```yaml
- name: Generate Evidence Pack
  run: |
    pip install git+https://github.com/tu-org/repo-analyzer.git
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

## 📚 Documentación Adicional

- [Guía de Seguridad](../SECURITY.md) - Análisis de vulnerabilidades
- [Guía de Calidad](../QUALITY.md) - Tests y cobertura
- [Documentación IA](../AI_DOCS.md) - Generación con IA
- [Guía de Upload](../UPLOAD.md) - Upload a plataformas externas
- [Integración Servidor](../INTEGRATION_SERVER.md) - Para plataformas receptoras
- [Setup Azure DevOps](../AZURE_DEVOPS_SETUP.md) - Integración con Azure

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🙏 Agradecimientos

- OpenAI y Google Gemini por las APIs de IA
- La comunidad de herramientas de análisis estático
- Todos los contribuidores

## 📧 Contacto

Para preguntas o soporte, abre un issue en GitHub o contacta al equipo de ingeniería.

---

**Hecho con ❤️ para automatizar documentación y compliance**