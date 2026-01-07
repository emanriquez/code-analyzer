"""Evidence pack generator module"""

import json
import os
import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import git

from .metrics_collector import MetricsCollector
from .security_analyzer import SecurityAnalyzer
from .quality_analyzer import QualityAnalyzer
from .ai_doc_generator import AIDocGenerator
from .scoring_system import ScoringSystem


class EvidenceGenerator:
    """Generates standardized evidence pack from analysis results"""
    
    def __init__(self, repo_path: str, output_dir: str, openai_token: Optional[str] = None,
                 gemini_token: Optional[str] = None, ai_provider: str = "auto", language: str = "en",
                 use_cache: bool = True):
        self.repo_path = Path(repo_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.openai_token = openai_token
        self.gemini_token = gemini_token
        self.ai_provider = ai_provider
        self.language = language
        self.use_cache = use_cache
    
    def generate(self, stack_info: Dict, deps_info: Dict, repo_facts: Dict, 
                 security_info: Optional[Dict] = None, quality_info: Optional[Dict] = None,
                 metrics: Optional[Dict] = None, summary: Optional[Dict] = None,
                 repo_name: Optional[str] = None, commit_sha: Optional[str] = None,
                 metrica_config_path: Optional[str] = None) -> Dict[str, str]:
        """Generate complete evidence pack"""
        generated_files = {}
        
        # Create directory structure
        (self.output_dir / "metrics").mkdir(exist_ok=True)
        (self.output_dir / "quality").mkdir(exist_ok=True)
        (self.output_dir / "security").mkdir(exist_ok=True)
        (self.output_dir / "change").mkdir(exist_ok=True)
        (self.output_dir / "docs").mkdir(exist_ok=True)
        (self.output_dir / "docs" / "api").mkdir(exist_ok=True)
        (self.output_dir / "diagrams").mkdir(exist_ok=True)
        (self.output_dir / "build").mkdir(exist_ok=True)
        
        # Generate summary.json
        summary = self._generate_summary(stack_info, deps_info, repo_facts)
        summary_path = self.output_dir / "summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        generated_files["summary.json"] = str(summary_path)
        
        # Generate dependencies.json
        deps_path = self.output_dir / "dependencies.json"
        with open(deps_path, 'w', encoding='utf-8') as f:
            json.dump(deps_info, f, indent=2)
        generated_files["dependencies.json"] = str(deps_path)
        
        # Generate repo_facts.json
        facts_path = self.output_dir / "repo_facts.json"
        with open(facts_path, 'w', encoding='utf-8') as f:
            json.dump(repo_facts, f, indent=2)
        generated_files["repo_facts.json"] = str(facts_path)
        
        # Generate metrics
        metrics_collector = MetricsCollector(str(self.repo_path))
        metrics = metrics_collector.collect()
        metrics_path = self.output_dir / "metrics" / "cloc.json"
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)
        generated_files["metrics/cloc.json"] = str(metrics_path)
        
        # Generate languages breakdown
        languages_data = {
            "primary_language": stack_info.get("primary_language", "Unknown"),
            "languages_breakdown": metrics.get("languages", {}),
            "total_files": metrics.get("files", 0),
            "total_lines": metrics.get("lines_of_code", 0),
        }
        languages_path = self.output_dir / "metrics" / "languages.json"
        with open(languages_path, 'w', encoding='utf-8') as f:
            json.dump(languages_data, f, indent=2)
        generated_files["metrics/languages.json"] = str(languages_path)
        
        # Generate change history
        change_info = self._generate_change_history()
        commits_path = self.output_dir / "change" / "commits.json"
        with open(commits_path, 'w', encoding='utf-8') as f:
            json.dump(change_info, f, indent=2)
        generated_files["change/commits.json"] = str(commits_path)
        
        changelog_path = self.output_dir / "change" / "changelog.md"
        with open(changelog_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_changelog_md(change_info))
        generated_files["change/changelog.md"] = str(changelog_path)
        
        # Generate security analysis
        if security_info:
            security_path = self.output_dir / "security" / "deps-sca.json"
            with open(security_path, 'w', encoding='utf-8') as f:
                json.dump(security_info, f, indent=2)
            generated_files["security/deps-sca.json"] = str(security_path)
        else:
            # Generate empty security report if no analysis was performed
            security_path = self.output_dir / "security" / "deps-sca.json"
            empty_security = {
                "scan_timestamp": datetime.now(timezone.utc).isoformat(),
                "note": "Security analysis not performed. Install security scanners (npm audit, safety, snyk, etc.)",
                "vulnerabilities": [],
                "summary": {
                    "total": 0,
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "info": 0,
                },
            }
            with open(security_path, 'w', encoding='utf-8') as f:
                json.dump(empty_security, f, indent=2)
            generated_files["security/deps-sca.json"] = str(security_path)
        
        # Generate quality analysis (tests and coverage)
        if quality_info:
            tests_path = self.output_dir / "quality" / "tests.json"
            with open(tests_path, 'w', encoding='utf-8') as f:
                json.dump(quality_info.get("test_results", {}), f, indent=2)
            generated_files["quality/tests.json"] = str(tests_path)
            
            coverage_path = self.output_dir / "quality" / "coverage-summary.json"
            coverage_data = quality_info.get("coverage") or {}
            with open(coverage_path, 'w', encoding='utf-8') as f:
                json.dump(coverage_data, f, indent=2)
            generated_files["quality/coverage-summary.json"] = str(coverage_path)
        else:
            # Generate empty quality reports if no analysis was performed
            tests_path = self.output_dir / "quality" / "tests.json"
            empty_tests = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0,
                "note": "Tests not executed. Configure test framework (Jest, pytest, etc.)"
            }
            with open(tests_path, 'w', encoding='utf-8') as f:
                json.dump(empty_tests, f, indent=2)
            generated_files["quality/tests.json"] = str(tests_path)
            
            coverage_path = self.output_dir / "quality" / "coverage-summary.json"
            empty_coverage = {
                "lines": 0,
                "statements": 0,
                "functions": 0,
                "branches": 0,
                "note": "Coverage not available. Run tests with coverage enabled."
            }
            with open(coverage_path, 'w', encoding='utf-8') as f:
                json.dump(empty_coverage, f, indent=2)
            generated_files["quality/coverage-summary.json"] = str(coverage_path)
        
        # Generate build info
        build_info = self._generate_build_info()
        build_path = self.output_dir / "build" / "build.json"
        with open(build_path, 'w', encoding='utf-8') as f:
            json.dump(build_info, f, indent=2)
        generated_files["build/build.json"] = str(build_path)
        
        # Generate documentation and diagrams with AI if token provided
        if self.openai_token or self.gemini_token:
            try:
                ai_generator = AIDocGenerator(
                    str(self.repo_path), 
                    openai_token=self.openai_token,
                    gemini_token=self.gemini_token,
                    provider=self.ai_provider,
                    language=self.language,
                    use_cache=self.use_cache
                )
                
                # Generate diagrams
                diagrams = ai_generator.generate_diagrams(
                    stack_info, deps_info, repo_facts, metrics or {}, summary or {}
                )
                
                if diagrams.get("c4_context"):
                    context_path = self.output_dir / "diagrams" / "c4_context.mmd"
                    with open(context_path, 'w', encoding='utf-8') as f:
                        f.write(diagrams["c4_context"])
                    generated_files["diagrams/c4_context.mmd"] = str(context_path)
                
                if diagrams.get("c4_container"):
                    container_path = self.output_dir / "diagrams" / "c4_container.mmd"
                    with open(container_path, 'w', encoding='utf-8') as f:
                        f.write(diagrams["c4_container"])
                    generated_files["diagrams/c4_container.mmd"] = str(container_path)
                
                # Generate sequence diagram (PlantUML)
                if diagrams.get("sequence"):
                    sequence_data = diagrams["sequence"]
                    if isinstance(sequence_data, dict):
                        sequence_code = sequence_data.get("code", "")
                        if sequence_code:
                            sequence_path = self.output_dir / "diagrams" / "sequence.puml"
                            with open(sequence_path, 'w', encoding='utf-8') as f:
                                f.write(sequence_code)
                            generated_files["diagrams/sequence.puml"] = str(sequence_path)
                            
                            # If PlantUML is available, render to image
                            if sequence_data.get("can_render"):
                                try:
                                    img_path = self.output_dir / "diagrams" / "sequence.png"
                                    subprocess.run(
                                        ['plantuml', '-tpng', str(sequence_path), '-o', str(self.output_dir / "diagrams")],
                                        check=True,
                                        timeout=30,
                                        capture_output=True
                                    )
                                    if img_path.exists():
                                        generated_files["diagrams/sequence.png"] = str(img_path)
                                except Exception:
                                    pass
                    elif isinstance(sequence_data, str):
                        sequence_path = self.output_dir / "diagrams" / "sequence.puml"
                        with open(sequence_path, 'w', encoding='utf-8') as f:
                            f.write(sequence_data)
                        generated_files["diagrams/sequence.puml"] = str(sequence_path)
                
                # Generate documentation
                docs = ai_generator.generate_documentation(
                    stack_info, deps_info, repo_facts, metrics or {},
                    security_info or {}, quality_info or {}, summary or {}
                )
                
                if docs.get("readme_enriched"):
                    readme_path = self.output_dir / "docs" / "README.enriched.md"
                    with open(readme_path, 'w', encoding='utf-8') as f:
                        f.write(docs["readme_enriched"])
                    generated_files["docs/README.enriched.md"] = str(readme_path)
                
                if docs.get("runbook"):
                    runbook_path = self.output_dir / "docs" / "runbook.md"
                    with open(runbook_path, 'w', encoding='utf-8') as f:
                        f.write(docs["runbook"])
                    generated_files["docs/runbook.md"] = str(runbook_path)
                
                if docs.get("architecture_doc"):
                    arch_path = self.output_dir / "docs" / "architecture.md"
                    with open(arch_path, 'w', encoding='utf-8') as f:
                        f.write(docs["architecture_doc"])
                    generated_files["docs/architecture.md"] = str(arch_path)
                    
            except Exception as e:
                # Fallback to basic documentation if AI fails
                pass  # Errors are handled by fallback generation
        
        # Copy original README from repo to docs/ if it exists
        original_readme_paths = [
            self.repo_path / "README.md",
            self.repo_path / "readme.md",
            self.repo_path / "README.txt",
            self.repo_path / "README.rst",
        ]
        
        for original_readme_path in original_readme_paths:
            if original_readme_path.exists() and original_readme_path.is_file():
                try:
                    # Copy original README to docs/
                    docs_readme_path = self.output_dir / "docs" / "README.md"
                    shutil.copy2(original_readme_path, docs_readme_path)
                    generated_files["docs/README.md"] = str(docs_readme_path)
                    break  # Only copy the first one found
                except Exception:
                    # If copy fails, try to read and write instead
                    try:
                        with open(original_readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        docs_readme_path = self.output_dir / "docs" / "README.md"
                        with open(docs_readme_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        generated_files["docs/README.md"] = str(docs_readme_path)
                        break
                    except Exception:
                        continue
        
        # Fallback to basic documentation if AI not available or failed
        if "docs/README.enriched.md" not in generated_files:
            readme_path = self.output_dir / "docs" / "README.enriched.md"
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(self._generate_enriched_readme(stack_info, deps_info, repo_facts))
            generated_files["docs/README.enriched.md"] = str(readme_path)
        
        if "docs/runbook.md" not in generated_files:
            runbook_path = self.output_dir / "docs" / "runbook.md"
            with open(runbook_path, 'w', encoding='utf-8') as f:
                f.write(self._generate_runbook_skeleton(stack_info))
            generated_files["docs/runbook.md"] = str(runbook_path)
        
        # Generate empty diagrams if AI didn't generate them
        if "diagrams/c4_context.mmd" not in generated_files:
            context_path = self.output_dir / "diagrams" / "c4_context.mmd"
            with open(context_path, 'w', encoding='utf-8') as f:
                f.write("# C4 Context Diagram\n\n*Generate with AI token (OpenAI/Gemini) to create diagram*\n")
            generated_files["diagrams/c4_context.mmd"] = str(context_path)
        
        if "diagrams/c4_container.mmd" not in generated_files:
            container_path = self.output_dir / "diagrams" / "c4_container.mmd"
            with open(container_path, 'w', encoding='utf-8') as f:
                f.write("# C4 Container Diagram\n\n*Generate with AI token (OpenAI/Gemini) to create diagram*\n")
            generated_files["diagrams/c4_container.mmd"] = str(container_path)
        
        if "diagrams/sequence.puml" not in generated_files:
            sequence_path = self.output_dir / "diagrams" / "sequence.puml"
            with open(sequence_path, 'w', encoding='utf-8') as f:
                f.write("@startuml\n# Sequence Diagram\n\n*Generate with AI token (OpenAI/Gemini) to create diagram*\n@enduml\n")
            generated_files["diagrams/sequence.puml"] = str(sequence_path)
        
        # Generate scoring/scores (calculate all 7 dimensions based on metrica.json)
        try:
            # Load stack_info, repo_facts, and metrics for intelligent scoring
            stack_info_data = {}
            repo_facts_data = {}
            metrics_data = {}
            
            # Try to load summary.json for stack_info
            summary_file = self.output_dir / "summary.json"
            if summary_file.exists():
                try:
                    with open(summary_file, 'r') as f:
                        summary_data = json.load(f)
                        stack_info_data = summary_data.get("tech_stack", {})
                except:
                    pass
            
            # Load repo_facts.json
            facts_file = self.output_dir / "repo_facts.json"
            if facts_file.exists():
                try:
                    with open(facts_file, 'r') as f:
                        repo_facts_data = json.load(f)
                except:
                    pass
            
            # Load metrics/cloc.json
            metrics_file = self.output_dir / "metrics" / "cloc.json"
            if metrics_file.exists():
                try:
                    with open(metrics_file, 'r') as f:
                        metrics_data = json.load(f)
                except:
                    pass
            
            scoring_system = ScoringSystem(
                str(self.output_dir),
                metrica_config_path=metrica_config_path,
                stack_info=stack_info_data,
                repo_facts=repo_facts_data,
                metrics=metrics_data
            )
            
            repo_name_value = repo_name or repo_facts.get("name", "unknown")
            commit_sha_value = commit_sha or repo_facts.get("commit_sha", "unknown")
            
            scores = scoring_system.calculate_scores(repo_name_value, commit_sha_value)
            
            score_path = self.output_dir / "score.json"
            with open(score_path, 'w', encoding='utf-8') as f:
                json.dump(scores, f, indent=2)
            generated_files["score.json"] = str(score_path)
        except Exception as e:
            # If scoring fails, continue without it
            pass
        
        # Generate checksums
        checksums = self._generate_checksums()
        checksums_path = self.output_dir / "SHA256SUMS"
        with open(checksums_path, 'w', encoding='utf-8') as f:
            for file_path, checksum in checksums.items():
                f.write(f"{checksum}  {file_path}\n")
        generated_files["SHA256SUMS"] = str(checksums_path)
        
        return generated_files
    
    def _generate_summary(self, stack_info: Dict, deps_info: Dict, repo_facts: Dict) -> Dict[str, Any]:
        """Generate summary.json"""
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repository": {
                "name": repo_facts.get("name", "unknown"),
                "url": repo_facts.get("url", ""),
                "commit_sha": repo_facts.get("commit_sha", ""),
                "branch": repo_facts.get("branch", ""),
            },
            "tech_stack": {
                "primary_language": stack_info.get("primary_language", "Unknown"),
                "frameworks": stack_info.get("frameworks", []),
                "package_manager": stack_info.get("package_manager"),
                "runtime": stack_info.get("runtime"),
                "has_typescript": stack_info.get("has_typescript", False),
                "is_mobile": stack_info.get("is_mobile", False),
            },
            "dependencies": {
                "total": deps_info.get("total_dependencies", 0),
                "runtime": len(deps_info.get("dependencies", [])),
                "dev": len(deps_info.get("dev_dependencies", [])),
                "package_manager": deps_info.get("package_manager"),
            },
            "evidence_pack_version": "1.0.0"
        }
    
    
    def _generate_change_history(self) -> Dict[str, Any]:
        """Extract git change history"""
        try:
            repo = git.Repo(self.repo_path)
            commits = []
            
            for commit in repo.iter_commits(max_count=100):
                commits.append({
                    "sha": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": {
                        "name": commit.author.name,
                        "email": commit.author.email,
                    },
                    "date": commit.committed_datetime.isoformat(),
                })
            
            tags = [tag.name for tag in repo.tags]
            
            return {
                "total_commits": len(commits),
                "recent_commits": commits[:20],  # Last 20 commits
                "tags": tags,
                "branches": [branch.name for branch in repo.branches],
            }
        except Exception as e:
            return {
                "error": f"Failed to extract git history: {str(e)}",
                "total_commits": 0,
                "recent_commits": [],
                "tags": [],
                "branches": [],
            }
    
    def _generate_changelog_md(self, change_info: Dict) -> str:
        """Generate markdown changelog"""
        md = "# Changelog\n\n"
        
        if "recent_commits" in change_info:
            md += "## Recent Commits\n\n"
            for commit in change_info["recent_commits"][:10]:
                md += f"### {commit['sha'][:7]} - {commit['date']}\n"
                md += f"**Author:** {commit['author']['name']}\n\n"
                md += f"{commit['message']}\n\n"
        
        if "tags" in change_info and change_info["tags"]:
            md += "## Tags\n\n"
            for tag in change_info["tags"]:
                md += f"- {tag}\n"
        
        return md
    
    def _generate_build_info(self) -> Dict[str, Any]:
        """Generate build information"""
        return {
            "build_id": os.environ.get("BUILD_BUILDID", "local"),
            "build_time": datetime.now(timezone.utc).isoformat(),
            "ci_cd": os.environ.get("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI", "local"),
        }
    
    def _generate_enriched_readme(self, stack_info: Dict, deps_info: Dict, repo_facts: Dict) -> str:
        """Generate enriched README"""
        md = f"# {repo_facts.get('name', 'Repository')}\n\n"
        md += f"**Generated:** {datetime.now(timezone.utc).isoformat()}\n\n"
        
        md += "## Tech Stack\n\n"
        md += f"- **Primary Language:** {stack_info.get('primary_language', 'Unknown')}\n"
        md += f"- **Frameworks:** {', '.join(stack_info.get('frameworks', []))}\n"
        md += f"- **Package Manager:** {stack_info.get('package_manager', 'N/A')}\n"
        md += f"- **Runtime:** {stack_info.get('runtime', 'N/A')}\n"
        if stack_info.get('has_typescript'):
            md += "- **TypeScript:** Yes\n"
        if stack_info.get('is_mobile'):
            md += "- **Mobile:** Yes (React Native)\n"
        
        md += "\n## Dependencies\n\n"
        md += f"- **Total:** {deps_info.get('total_dependencies', 0)}\n"
        md += f"- **Runtime:** {len(deps_info.get('dependencies', []))}\n"
        md += f"- **Dev:** {len(deps_info.get('dev_dependencies', []))}\n"
        
        return md
    
    def _generate_runbook_skeleton(self, stack_info: Dict) -> str:
        """Generate runbook skeleton"""
        md = "# Runbook\n\n"
        md += "## Overview\n\n"
        md += "Operational runbook for this service.\n\n"
        
        md += "## Tech Stack\n\n"
        md += f"- **Language:** {stack_info.get('primary_language', 'Unknown')}\n"
        md += f"- **Frameworks:** {', '.join(stack_info.get('frameworks', []))}\n\n"
        
        md += "## Deployment\n\n"
        md += "### Prerequisites\n\n"
        md += "- [ ] Add prerequisites\n\n"
        
        md += "### Steps\n\n"
        md += "1. [ ] Add deployment steps\n\n"
        
        md += "## Monitoring\n\n"
        md += "- [ ] Add monitoring information\n\n"
        
        md += "## Troubleshooting\n\n"
        md += "- [ ] Add common issues and solutions\n\n"
        
        return md
    
    def _generate_checksums(self) -> Dict[str, str]:
        """Generate SHA256 checksums for all files"""
        checksums = {}
        
        for file_path in self.output_dir.rglob("*"):
            if file_path.is_file() and file_path.name != "SHA256SUMS":
                relative_path = file_path.relative_to(self.output_dir)
                with open(file_path, 'rb') as f:
                    checksum = hashlib.sha256(f.read()).hexdigest()
                    checksums[str(relative_path)] = checksum
        
        return checksums

