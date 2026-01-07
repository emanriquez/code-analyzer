"""AI-powered documentation and diagram generation using OpenAI and Gemini"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime

# Optional imports for AI providers
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

from .cache_manager import CacheManager


class AIDocGenerator:
    """Generates documentation and diagrams using OpenAI or Gemini"""
    
    def __init__(self, repo_path: str, openai_token: Optional[str] = None, 
                 gemini_token: Optional[str] = None, provider: Literal["openai", "gemini", "auto"] = "auto",
                 language: str = "en", use_cache: bool = True):
        self.repo_path = Path(repo_path)
        self.openai_token = openai_token or os.environ.get('OPENAI_API_KEY')
        self.gemini_token = gemini_token or os.environ.get('GEMINI_API_KEY')
        self.language = language.lower()
        self.use_cache = use_cache
        self.cache_manager = CacheManager() if use_cache else None
        
        # Determine provider based on available tokens
        if provider == "auto":
            # Auto-select: use the provider that has a token
            if self.openai_token and not self.gemini_token:
                self.provider = "openai"
            elif self.gemini_token and not self.openai_token:
                self.provider = "gemini"
            elif self.openai_token and self.gemini_token:
                # Both available, prefer OpenAI
                self.provider = "openai"
            else:
                self.provider = None
        else:
            # Use specified provider if token is available
            if provider == "openai" and self.openai_token:
                self.provider = "openai"
            elif provider == "gemini" and self.gemini_token:
                self.provider = "gemini"
            else:
                # Provider specified but no token, try to use what's available
                if self.openai_token:
                    self.provider = "openai"
                elif self.gemini_token:
                    self.provider = "gemini"
                else:
                    self.provider = None
        
        # Initialize clients - only initialize the one we're using
        self.openai_client = None
        self.gemini_client = None
        
        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI package not installed. Install with: pip install openai")
            if not self.openai_token:
                raise ValueError("OpenAI provider selected but no OpenAI token provided")
            self.openai_client = OpenAI(api_key=self.openai_token)
        
        elif self.provider == "gemini":
            if not GEMINI_AVAILABLE:
                raise ImportError("Google Generative AI package not installed. Install with: pip install google-generativeai")
            if not self.gemini_token:
                raise ValueError("Gemini provider selected but no Gemini token provided")
            genai.configure(api_key=self.gemini_token)
            self.gemini_client = genai.GenerativeModel('gemini-pro')
        
        # Load existing README if available
        self.existing_readme = self._get_existing_readme()
    
    def _get_existing_readme(self) -> Optional[str]:
        """Get existing README content if available in the repository root"""
        readme_paths = [
            self.repo_path / "README.md",
            self.repo_path / "readme.md",
            self.repo_path / "README.txt",
            self.repo_path / "README.rst",
        ]
        
        for readme_path in readme_paths:
            if readme_path.exists() and readme_path.is_file():
                try:
                    with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().strip()
                        if content:  # Only return if not empty
                            return content
                except Exception:
                    # If can't read, try next path
                    continue
        
        return None
    
    def _get_readme_context(self) -> str:
        """Get README context to include in prompts"""
        if self.existing_readme:
            # Limit README content to avoid token limits (keep first 3000 chars)
            readme_preview = self.existing_readme[:3000]
            if len(self.existing_readme) > 3000:
                readme_preview += "\n\n[... contenido del README truncado ...]"
            return f"""

=== EXISTING PROJECT README (use this as primary context to understand what the system does) ===
{readme_preview}
=== END OF README ===
"""
        return ""
    
    def generate_diagrams(self, stack_info: Dict, deps_info: Dict, repo_facts: Dict, 
                         metrics: Dict, summary: Dict) -> Dict[str, str]:
        """Generate C4 diagrams in Mermaid format and sequence diagrams"""
        if not self.provider:
            return {
                "c4_context": None,
                "c4_container": None,
                "sequence": None,
                "error": "No AI provider token provided"
            }
        
        diagrams = {}
        
        # Generate C4 Context diagram
        try:
            context_diagram = self._generate_c4_context_diagram(
                stack_info, deps_info, repo_facts, summary
            )
            diagrams["c4_context"] = context_diagram
        except Exception as e:
            diagrams["c4_context"] = None
            diagrams["c4_context_error"] = str(e)
        
        # Generate C4 Container diagram
        try:
            container_diagram = self._generate_c4_container_diagram(
                stack_info, deps_info, repo_facts, metrics, summary
            )
            diagrams["c4_container"] = container_diagram
        except Exception as e:
            diagrams["c4_container"] = None
            diagrams["c4_container_error"] = str(e)
        
        # Generate Sequence diagram
        try:
            sequence_diagram = self._generate_sequence_diagram(
                stack_info, deps_info, repo_facts, summary
            )
            diagrams["sequence"] = sequence_diagram
        except Exception as e:
            diagrams["sequence"] = None
            diagrams["sequence_error"] = str(e)
        
        return diagrams
    
    def generate_documentation(self, stack_info: Dict, deps_info: Dict, repo_facts: Dict,
                               metrics: Dict, security_info: Dict, quality_info: Dict,
                               summary: Dict) -> Dict[str, str]:
        """Generate enhanced documentation using AI"""
        if not self.provider:
            return {
                "readme_enriched": None,
                "runbook": None,
                "architecture_doc": None,
                "error": "No AI provider token provided"
            }
        
        docs = {}
        
        # Generate enriched README
        try:
            readme = self._generate_enriched_readme(
                stack_info, deps_info, repo_facts, metrics, security_info, quality_info, summary
            )
            docs["readme_enriched"] = readme
        except Exception as e:
            docs["readme_enriched"] = None
            docs["readme_error"] = str(e)
        
        # Generate runbook
        try:
            runbook = self._generate_runbook(
                stack_info, deps_info, repo_facts, metrics, summary
            )
            docs["runbook"] = runbook
        except Exception as e:
            docs["runbook"] = None
            docs["runbook_error"] = str(e)
        
        # Generate architecture documentation
        try:
            architecture = self._generate_architecture_doc(
                stack_info, deps_info, repo_facts, metrics, summary
            )
            docs["architecture_doc"] = architecture
        except Exception as e:
            docs["architecture_doc"] = None
            docs["architecture_error"] = str(e)
        
        return docs
    
    def _call_ai(self, prompt: str, system_prompt: Optional[str] = None, 
                 model: Optional[str] = None, max_tokens: int = 2000) -> str:
        """Call AI provider (OpenAI or Gemini) - only uses the provider that has a token"""
        if not self.provider:
            raise Exception("No AI provider available. Provide OpenAI or Gemini token.")
        
        # Check cache first
        if self.use_cache and self.cache_manager:
            cache_data = {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "provider": self.provider,
            }
            cache_key = self.cache_manager.get_cache_key("ai_call", cache_data)
            cached = self.cache_manager.get(cache_key)
            if cached:
                return cached
        
        try:
            # Only call the provider that was initialized (has token)
            if self.provider == "openai":
                if not self.openai_client:
                    raise Exception("OpenAI client not initialized. Token may be missing.")
                response = self._call_openai(prompt, system_prompt, model or "gpt-4o-mini", max_tokens)
            elif self.provider == "gemini":
                if not self.gemini_client:
                    raise Exception("Gemini client not initialized. Token may be missing.")
                response = self._call_gemini(prompt, system_prompt, model or "gemini-pro")
            else:
                raise Exception(f"Unknown provider: {self.provider}")
            
            # Cache the response
            if self.use_cache and self.cache_manager:
                cache_data = {
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "provider": self.provider,
                }
                cache_key = self.cache_manager.get_cache_key("ai_call", cache_data)
                self.cache_manager.set(cache_key, response)
            
            return response
        except Exception as e:
            raise Exception(f"AI API error ({self.provider}): {str(e)}")
    
    def _call_openai(self, prompt: str, system_prompt: Optional[str] = None, 
                     model: str = "gpt-4o-mini", max_tokens: int = 2000) -> str:
        """Call OpenAI API"""
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    def _call_gemini(self, prompt: str, system_prompt: Optional[str] = None,
                     model: str = "gemini-pro") -> str:
        """Call Gemini API"""
        if not self.gemini_client:
            raise Exception("Gemini client not initialized")
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = self.gemini_client.generate_content(full_prompt)
        return response.text.strip()
    
    def _get_language_instruction(self) -> str:
        """Get language instruction for prompts"""
        language_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "pt": "Portuguese",
            "it": "Italian",
            "ja": "Japanese",
            "zh": "Chinese",
            "ru": "Russian",
        }
        lang_name = language_names.get(self.language, self.language.upper())
        return f"IMPORTANT: Generate all text, labels, and descriptions in {lang_name} ({self.language})."
    
    def _generate_c4_context_diagram(self, stack_info: Dict, deps_info: Dict,
                                     repo_facts: Dict, summary: Dict) -> str:
        """Generate C4 Context diagram in Mermaid format"""
        system_prompt = """You are an expert software architect. Generate C4 Context diagrams in Mermaid format.
The diagram should show the system in context with external users and systems.
Use the existing README to understand what the system does and its purpose."""
        
        lang_instruction = self._get_language_instruction()
        readme_context = self._get_readme_context()
        
        prompt = f"""{lang_instruction}
{readme_context}

Generate a C4 Context diagram in Mermaid format for this software system:

Repository: {repo_facts.get('name', 'Unknown')}
Primary Language: {stack_info.get('primary_language', 'Unknown')}
Frameworks: {', '.join(stack_info.get('frameworks', []))}
Package Manager: {stack_info.get('package_manager', 'Unknown')}
Runtime: {stack_info.get('runtime', 'Unknown')}

Dependencies: {deps_info.get('total_dependencies', 0)} total dependencies
Main Dependencies: {', '.join([d.get('name', '') for d in deps_info.get('dependencies', [])[:10]])}

IMPORTANT: Use the existing README above to understand what this system does, its purpose, and main features.
This will help you create an accurate context diagram that reflects the actual system functionality.

Generate ONLY the Mermaid diagram code, starting with ```mermaid and ending with ```.
The diagram should follow C4 Context level conventions showing:
- The software system as the main element
- External users (if applicable)
- External systems it interacts with
- Relationships between them

Use proper Mermaid syntax for C4 diagrams."""
        
        response = self._call_ai(prompt, system_prompt, max_tokens=1500)
        return self._extract_code_block(response, "mermaid")
    
    def _generate_c4_container_diagram(self, stack_info: Dict, deps_info: Dict,
                                       repo_facts: Dict, metrics: Dict, summary: Dict) -> str:
        """Generate C4 Container diagram in Mermaid format"""
        system_prompt = """You are an expert software architect. Generate C4 Container diagrams in Mermaid format.
The diagram should show the containers (applications, databases, etc.) within the system.
Use the existing README to understand what the system does and its architecture."""
        
        lang_instruction = self._get_language_instruction()
        readme_context = self._get_readme_context()
        
        prompt = f"""{lang_instruction}
{readme_context}

Generate a C4 Container diagram in Mermaid format for this software system:

Repository: {repo_facts.get('name', 'Unknown')}
Primary Language: {stack_info.get('primary_language', 'Unknown')}
Frameworks: {', '.join(stack_info.get('frameworks', []))}
Package Manager: {stack_info.get('package_manager', 'Unknown')}
Runtime: {stack_info.get('runtime', 'Unknown')}

Lines of Code: {metrics.get('lines_of_code', 0)}
Files: {metrics.get('files', 0)}
Languages: {', '.join(list(metrics.get('languages', {}).keys())[:5])}

Key Dependencies:
{json.dumps([d.get('name', '') for d in deps_info.get('dependencies', [])[:15]], indent=2)}

IMPORTANT: Use the existing README above to understand what this system does and its main components.
This will help you create an accurate container diagram that reflects the actual system architecture.

Generate ONLY the Mermaid diagram code, starting with ```mermaid and ending with ```.
The diagram should follow C4 Container level conventions showing:
- Containers (web applications, APIs, databases, file systems, etc.)
- External systems
- Relationships and data flows between containers
- Technology choices for each container

Use proper Mermaid syntax for C4 diagrams."""
        
        response = self._call_ai(prompt, system_prompt, max_tokens=2000)
        return self._extract_code_block(response, "mermaid")
    
    def _generate_sequence_diagram(self, stack_info: Dict, deps_info: Dict,
                                  repo_facts: Dict, summary: Dict) -> Dict[str, Any]:
        """Generate Sequence diagram in PlantUML format"""
        system_prompt = """You are an expert software architect. Generate sequence diagrams in PlantUML format.
The diagram should show interactions between system components.
Use the existing README to understand what the system does and its workflows."""
        
        lang_instruction = self._get_language_instruction()
        readme_context = self._get_readme_context()
        
        prompt = f"""{lang_instruction}
{readme_context}

Generate a sequence diagram in PlantUML format for this software system:

Repository: {repo_facts.get('name', 'Unknown')}
Primary Language: {stack_info.get('primary_language', 'Unknown')}
Frameworks: {', '.join(stack_info.get('frameworks', []))}
Runtime: {stack_info.get('runtime', 'Unknown')}

Key Dependencies:
{json.dumps([d.get('name', '') for d in deps_info.get('dependencies', [])[:15]], indent=2)}

IMPORTANT: Use the existing README above to understand what this system does and its main workflows.
This will help you create an accurate sequence diagram that reflects the actual system interactions.

Generate ONLY the PlantUML diagram code, starting with @startuml and ending with @enduml.
The diagram should show:
- Main actors/users
- System components
- Interactions and message flows
- Return messages
- Optional: activation boxes, notes, loops

Use proper PlantUML syntax for sequence diagrams."""
        
        response = self._call_ai(prompt, system_prompt, max_tokens=2000)
        plantuml_code = self._extract_code_block(response, "plantuml") or response
        
        # Ensure it has PlantUML markers
        if not plantuml_code.strip().startswith("@startuml"):
            plantuml_code = "@startuml\n" + plantuml_code
        if not plantuml_code.strip().endswith("@enduml"):
            plantuml_code = plantuml_code + "\n@enduml"
        
        # Return code and metadata
        result = {
            "code": plantuml_code,
            "format": "plantuml",
            "can_render": self._check_plantuml_available()
        }
        
        return result
    
    def _check_plantuml_available(self) -> bool:
        """Check if PlantUML is installed"""
        try:
            result = subprocess.run(
                ['plantuml', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _generate_enriched_readme(self, stack_info: Dict, deps_info: Dict, repo_facts: Dict,
                                  metrics: Dict, security_info: Dict, quality_info: Dict,
                                  summary: Dict) -> str:
        """Generate enriched README with AI"""
        lang_instruction = self._get_language_instruction()
        readme_context = self._get_readme_context()
        
        system_prompt = f"""You are a technical writer. Generate comprehensive, professional README documentation
for software projects. Include all relevant sections with clear, concise information.
Use the existing README as a base and enhance it with additional technical details.
{lang_instruction}"""
        
        if readme_context:
            readme_base_instruction = """
IMPORTANT: An existing README is provided below. Use it as the foundation and enhance it with:
- Additional technical details discovered from the codebase analysis
- Missing sections that should be in a comprehensive README
- Updated or more detailed information where needed
- Keep the original tone and style when possible
"""
        else:
            readme_base_instruction = """
IMPORTANT: No existing README found. Generate a complete README from scratch based on the available information.
"""
        
        prompt = f"""{lang_instruction}
{readme_context}
{readme_base_instruction}

Generate a comprehensive README.md for this software project:

Repository: {repo_facts.get('name', 'Unknown')}
Description: {repo_facts.get('url', 'No description available')}

Tech Stack:
- Primary Language: {stack_info.get('primary_language', 'Unknown')}
- Frameworks: {', '.join(stack_info.get('frameworks', []))}
- Package Manager: {stack_info.get('package_manager', 'Unknown')}
- Runtime: {stack_info.get('runtime', 'Unknown')}
- TypeScript: {'Yes' if stack_info.get('has_typescript') else 'No'}
- Mobile: {'Yes (React Native)' if stack_info.get('is_mobile') else 'No'}

Code Metrics:
- Lines of Code: {metrics.get('lines_of_code', 0)}
- Files: {metrics.get('files', 0)}
- Languages: {', '.join(list(metrics.get('languages', {}).keys()))}

Dependencies: {deps_info.get('total_dependencies', 0)} total
Security: {security_info.get('summary', {}).get('total', 0)} vulnerabilities found
Quality: {quality_info.get('test_results', {}).get('total', 0)} tests, 
         {quality_info.get('coverage', {}).get('lines', 0)}% coverage

Generate a complete README.md with:
1. Project title and description
2. Features
3. Tech stack overview
4. Installation instructions
5. Usage/Getting started
6. Project structure
7. Testing
8. Security considerations
9. Contributing (if applicable)
10. License (if applicable)

Make it professional, clear, and comprehensive."""
        
        response = self._call_ai(prompt, system_prompt, max_tokens=3000)
        return self._extract_code_block(response, "markdown") or response
    
    def _generate_runbook(self, stack_info: Dict, deps_info: Dict, repo_facts: Dict,
                          metrics: Dict, summary: Dict) -> str:
        """Generate operational runbook"""
        lang_instruction = self._get_language_instruction()
        readme_context = self._get_readme_context()
        
        system_prompt = f"""You are a DevOps engineer. Generate operational runbooks for software systems.
Include deployment, monitoring, troubleshooting, and maintenance procedures.
Use the existing README to understand what the system does and its operational requirements.
{lang_instruction}"""
        
        prompt = f"""{lang_instruction}
{readme_context}

Generate an operational runbook for this software system:

Repository: {repo_facts.get('name', 'Unknown')}
Tech Stack:
- Language: {stack_info.get('primary_language', 'Unknown')}
- Frameworks: {', '.join(stack_info.get('frameworks', []))}
- Package Manager: {stack_info.get('package_manager', 'Unknown')}
- Runtime: {stack_info.get('runtime', 'Unknown')}

IMPORTANT: Use the existing README above to understand what this system does, its purpose, and operational needs.
This will help you create a practical runbook that reflects the actual system requirements.

Generate a comprehensive runbook with:
1. System Overview
2. Prerequisites and Dependencies
3. Deployment Procedures
4. Configuration Management
5. Monitoring and Alerting
6. Common Issues and Troubleshooting
7. Rollback Procedures
8. Maintenance Windows
9. Contact Information

Make it practical and actionable for operations teams."""
        
        response = self._call_ai(prompt, system_prompt, max_tokens=2500)
        return self._extract_code_block(response, "markdown") or response
    
    def _generate_architecture_doc(self, stack_info: Dict, deps_info: Dict, repo_facts: Dict,
                                   metrics: Dict, summary: Dict) -> str:
        """Generate architecture documentation"""
        lang_instruction = self._get_language_instruction()
        readme_context = self._get_readme_context()
        
        system_prompt = f"""You are a software architect. Generate comprehensive architecture documentation
that explains system design, components, and technical decisions.
Use the existing README to understand what the system does and its architectural purpose.
{lang_instruction}"""
        
        prompt = f"""{lang_instruction}
{readme_context}

Generate architecture documentation for this software system:

Repository: {repo_facts.get('name', 'Unknown')}
Tech Stack:
- Language: {stack_info.get('primary_language', 'Unknown')}
- Frameworks: {', '.join(stack_info.get('frameworks', []))}
- Package Manager: {stack_info.get('package_manager', 'Unknown')}
- Runtime: {stack_info.get('runtime', 'Unknown')}

Code Metrics:
- Lines of Code: {metrics.get('lines_of_code', 0)}
- Files: {metrics.get('files', 0)}

Key Dependencies:
{json.dumps([d.get('name', '') for d in deps_info.get('dependencies', [])[:20]], indent=2)}

IMPORTANT: Use the existing README above to understand what this system does, its purpose, and main features.
This will help you create accurate architecture documentation that reflects the actual system design and purpose.

Generate comprehensive architecture documentation with:
1. System Overview
2. Architecture Patterns
3. Component Design
4. Data Flow
5. Technology Choices and Rationale
6. Scalability Considerations
7. Security Architecture
8. Integration Points

Make it detailed and suitable for technical stakeholders."""
        
        response = self._call_ai(prompt, system_prompt, max_tokens=3000)
        return self._extract_code_block(response, "markdown") or response
    
    def _extract_code_block(self, text: str, language: str = "mermaid") -> str:
        """Extract code block from AI response"""
        # Try different code block formats
        patterns = [
            f"```{language}",
            f"``` {language}",
            "```mermaid",
            "```plantuml",
            "```markdown",
            "```",
        ]
        
        for pattern in patterns:
            if pattern in text:
                parts = text.split(pattern, 1)
                if len(parts) > 1:
                    code = parts[1].split("```")[0].strip()
                    return code
        
        # If no code block found, return the text as-is
        return text.strip()
