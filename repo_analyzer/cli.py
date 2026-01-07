"""CLI entry point for repo-analyzer"""

import os
import sys
import click
from pathlib import Path
from typing import Optional

from .stack_detector import StackDetector
from .dependency_parser import DependencyParser
from .evidence_generator import EvidenceGenerator
from .repo_facts import RepoFactsCollector
from .security_analyzer import SecurityAnalyzer
from .quality_analyzer import QualityAnalyzer
from .uploader import EvidenceUploader


@click.command()
@click.option('--repo', '-r', default='.', help='Repository path to analyze')
@click.option('--out', '-o', default='./out', help='Output directory for evidence pack')
@click.option('--upload-url', envvar='EVIDENCE_UPLOAD_URL', help='Base URL for uploading evidence pack')
@click.option('--upload-token', envvar='EVIDENCE_UPLOAD_TOKEN', help='Auth token for upload')
@click.option('--upload-method', type=click.Choice(['zip', 'individual']), default='zip', help='Upload method: zip (single file) or individual (file by file)')
@click.option('--upload-auth-type', type=click.Choice(['bearer', 'sas', 'custom']), default='bearer', help='Authentication type for upload')
@click.option('--upload-custom-header', help='Custom header name for authentication (if auth-type is custom)')
@click.option('--repo-name', envvar='BUILD_REPOSITORY_NAME', help='Repository name')
@click.option('--commit-sha', envvar='BUILD_SOURCEVERSION', help='Commit SHA')
@click.option('--build-id', envvar='BUILD_BUILDID', help='Build ID')
@click.option('--snyk-token', envvar='SNYK_TOKEN', default='319d14cb-7e62-4d05-b8f2-1c5fde4dbc2202', help='Snyk authentication token')
@click.option('--openai-token', envvar='OPENAI_API_KEY', help='OpenAI API token for generating diagrams and documentation')
@click.option('--gemini-token', envvar='GEMINI_API_KEY', help='Google Gemini API token for generating diagrams and documentation')
@click.option('--ai-provider', type=click.Choice(['openai', 'gemini', 'auto']), default='auto', help='AI provider to use (auto selects based on available tokens)')
@click.option('--language', '--lang', default='en', help='Language for generated documentation (en, es, fr, de, pt, etc.)')
@click.option('--no-cache', is_flag=True, help='Disable cache for AI-generated content')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def main(repo: str, out: str, upload_url: Optional[str], upload_token: Optional[str],
         upload_method: str, upload_auth_type: str, upload_custom_header: Optional[str],
         repo_name: Optional[str], commit_sha: Optional[str], build_id: Optional[str],
         snyk_token: Optional[str], openai_token: Optional[str], gemini_token: Optional[str],
         ai_provider: str, language: str, no_cache: bool, verbose: bool):
    """Analyze repository and generate evidence pack"""
    
    repo_path = Path(repo).resolve()
    output_dir = Path(out).resolve()
    
    if not repo_path.exists():
        click.echo(f"Error: Repository path does not exist: {repo_path}", err=True)
        sys.exit(1)
    
    if verbose:
        click.echo(f"Analyzing repository: {repo_path}")
        click.echo(f"Output directory: {output_dir}")
    
    try:
        # Step 1: Detect tech stack
        if verbose:
            click.echo("Detecting tech stack...")
        detector = StackDetector(str(repo_path))
        tech_stack = detector.detect()
        
        stack_info = {
            "primary_language": tech_stack.primary_language,
            "frameworks": tech_stack.frameworks,
            "package_manager": tech_stack.package_manager,
            "build_tool": tech_stack.build_tool,
            "runtime": tech_stack.runtime,
            "has_typescript": tech_stack.has_typescript,
            "is_mobile": tech_stack.is_mobile,
            "detected_files": tech_stack.detected_files,
        }
        
        if verbose:
            click.echo(f"  Primary Language: {tech_stack.primary_language}")
            click.echo(f"  Frameworks: {', '.join(tech_stack.frameworks) if tech_stack.frameworks else 'None'}")
            click.echo(f"  Package Manager: {tech_stack.package_manager or 'None'}")
            click.echo(f"  TypeScript: {tech_stack.has_typescript}")
            click.echo(f"  Mobile: {tech_stack.is_mobile}")
        
        # Step 2: Parse dependencies
        if verbose:
            click.echo("Parsing dependencies...")
        parser = DependencyParser(str(repo_path))
        deps_info = parser.parse()
        
        if verbose:
            click.echo(f"  Total Dependencies: {deps_info.get('total_dependencies', 0)}")
            click.echo(f"  Package Manager: {deps_info.get('package_manager', 'Unknown')}")
        
        # Step 3: Collect repository facts
        if verbose:
            click.echo("Collecting repository facts...")
        facts_collector = RepoFactsCollector(str(repo_path))
        repo_facts = facts_collector.collect(
            repo_name=repo_name,
            commit_sha=commit_sha,
            build_id=build_id
        )
        
        if verbose:
            click.echo(f"  Repository: {repo_facts.get('name', 'Unknown')}")
            click.echo(f"  Commit: {repo_facts.get('commit_sha', 'Unknown')[:7]}")
        
        # Step 4: Security analysis
        security_info = None
        if verbose:
            click.echo("Running security analysis...")
        try:
            security_analyzer = SecurityAnalyzer(str(repo_path), snyk_token=snyk_token)
            security_info = security_analyzer.analyze(deps_info, stack_info)
            
            if verbose and snyk_token:
                click.echo(f"  Snyk Code token: {'configured' if snyk_token else 'not provided'}")
            
            if verbose:
                summary = security_info.get("summary", {})
                click.echo(f"  Scanner: {security_info.get('scan_method', 'none')}")
                click.echo(f"  Vulnerabilities: {summary.get('total', 0)}")
                if summary.get('total', 0) > 0:
                    click.echo(f"    Critical: {summary.get('critical', 0)}")
                    click.echo(f"    High: {summary.get('high', 0)}")
                    click.echo(f"    Medium: {summary.get('medium', 0)}")
                    click.echo(f"    Low: {summary.get('low', 0)}")
        except Exception as e:
            if verbose:
                click.echo(f"  Security analysis failed: {str(e)}")
        
        # Step 5: Quality analysis (tests and coverage)
        quality_info = None
        if verbose:
            click.echo("Running quality analysis (tests and coverage)...")
        try:
            quality_analyzer = QualityAnalyzer(str(repo_path))
            quality_info = quality_analyzer.analyze(stack_info)
            
            if verbose:
                test_results = quality_info.get("test_results", {})
                click.echo(f"  Test Framework: {quality_info.get('test_framework', 'none')}")
                click.echo(f"  Tests: {test_results.get('total', 0)} total")
                if test_results.get('total', 0) > 0:
                    click.echo(f"    Passed: {test_results.get('passed', 0)}")
                    click.echo(f"    Failed: {test_results.get('failed', 0)}")
                    click.echo(f"    Skipped: {test_results.get('skipped', 0)}")
                
                coverage = quality_info.get("coverage")
                if coverage:
                    click.echo(f"  Coverage:")
                    click.echo(f"    Lines: {coverage.get('lines', 0)}%")
                    click.echo(f"    Branches: {coverage.get('branches', 0)}%")
        except Exception as e:
            if verbose:
                click.echo(f"  Quality analysis failed: {str(e)}")
        
        # Step 6: Collect metrics for AI generation
        if verbose:
            click.echo("Collecting metrics for AI generation...")
        from .metrics_collector import MetricsCollector
        metrics_collector = MetricsCollector(str(repo_path))
        metrics = metrics_collector.collect()
        
        # Generate summary for AI
        from datetime import datetime
        summary = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "repository": {
                "name": repo_facts.get("name", "unknown"),
                "url": repo_facts.get("url", ""),
                "commit_sha": repo_facts.get("commit_sha", ""),
            },
            "tech_stack": {
                "primary_language": stack_info.get("primary_language", "Unknown"),
                "frameworks": stack_info.get("frameworks", []),
            },
            "dependencies": {
                "total": deps_info.get("total_dependencies", 0),
            },
        }
        
        # Step 7: Generate evidence pack
        if verbose:
            click.echo("Generating evidence pack...")
            if openai_token or gemini_token:
                provider_name = ai_provider if ai_provider != "auto" else ("OpenAI" if openai_token else "Gemini")
                click.echo(f"  AI Provider: {provider_name} (will generate AI-powered docs and diagrams)")
                click.echo(f"  Language: {language}")
                if no_cache:
                    click.echo("  Cache: disabled")
                else:
                    click.echo("  Cache: enabled")
            else:
                click.echo("  AI tokens: not provided (using basic templates)")
        
        generator = EvidenceGenerator(
            str(repo_path), 
            str(output_dir), 
            openai_token=openai_token,
            gemini_token=gemini_token,
            ai_provider=ai_provider,
            use_cache=not no_cache
        )
        generated_files = generator.generate(
            stack_info, deps_info, repo_facts, security_info, quality_info, metrics, summary
        )
        
        if verbose:
            click.echo(f"Generated {len(generated_files)} files:")
            for file_path in generated_files.values():
                click.echo(f"  - {file_path}")
            
            # Show metrics summary
            import json
            metrics_path = output_dir / "metrics" / "cloc.json"
            if metrics_path.exists():
                with open(metrics_path, 'r') as f:
                    metrics = json.load(f)
                    click.echo(f"\nMetrics:")
                    click.echo(f"  Total Files: {metrics.get('files', 0)}")
                    click.echo(f"  Lines of Code: {metrics.get('lines_of_code', 0)}")
                    click.echo(f"  Method: {metrics.get('method', 'unknown')}")
                    if metrics.get('languages'):
                        click.echo(f"  Languages: {len(metrics['languages'])}")
        
        # Step 8: Upload if URL provided
        published_url = None
        if upload_url and upload_token:
            if verbose:
                click.echo(f"Uploading evidence pack ({upload_method})...")
            try:
                uploader = EvidenceUploader(
                    upload_url=upload_url,
                    upload_token=upload_token,
                    auth_type=upload_auth_type,
                    custom_header=upload_custom_header
                )
                
                upload_result = uploader.upload(
                    evidence_dir=output_dir,
                    repo_name=repo_facts.get('name', 'repo'),
                    commit_sha=repo_facts.get('commit_sha', 'unknown'),
                    upload_method=upload_method
                )
                
                if upload_result.get('success'):
                    published_url = upload_result.get('published_url')
                    if verbose:
                        click.echo(f"  Upload successful!")
                        click.echo(f"  Method: {upload_result.get('upload_method')}")
                        if upload_result.get('file_size'):
                            size_mb = upload_result.get('file_size') / (1024 * 1024)
                            click.echo(f"  Size: {size_mb:.2f} MB")
                        if upload_result.get('total_files'):
                            click.echo(f"  Files uploaded: {upload_result.get('total_files')}")
                        click.echo(f"  Published URL: {published_url}")
                else:
                    click.echo(f"  Upload completed with errors", err=True)
                    if upload_result.get('failed_files'):
                        click.echo(f"  Failed files: {len(upload_result.get('failed_files', []))}")
                    published_url = upload_result.get('published_url')
                    
            except Exception as e:
                click.echo(f"  Upload failed: {str(e)}", err=True)
                if verbose:
                    import traceback
                    traceback.print_exc()
        else:
            if verbose:
                click.echo("Skipping upload (no URL/token provided)")
        
        # Output summary
        summary_path = output_dir / "summary.json"
        click.echo(f"\n✓ Evidence pack generated successfully!")
        click.echo(f"  Output directory: {output_dir}")
        click.echo(f"  Summary: {summary_path}")
        
        if published_url:
            click.echo(f"  Published URL: {published_url}")
            # Export as environment variable for CI/CD
            print(f"\nEVIDENCE_PUBLISHED_URL={published_url}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

