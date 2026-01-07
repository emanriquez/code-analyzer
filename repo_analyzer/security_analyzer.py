"""Security analysis module for code and dependency vulnerability scanning"""

import json
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests


class SecurityAnalyzer:
    """Analyzes security vulnerabilities in source code using SAST (Static Application Security Testing)"""
    
    def __init__(self, repo_path: str, snyk_token: Optional[str] = None, verbose: bool = False):
        self.repo_path = Path(repo_path)
        self.snyk_token = snyk_token or os.environ.get('SNYK_TOKEN')
        self.verbose = verbose
        self.debug_logs = []
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setLevel(logging.DEBUG if verbose else logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    def _debug(self, message: str):
        """Log debug message"""
        self.debug_logs.append(message)
        if self.verbose:
            self.logger.debug(message)
            print(f"[DEBUG Security] {message}", file=sys.stderr, flush=True)
    
    def analyze(self, deps_info: Dict[str, Any], stack_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform code security analysis (SAST only, no dependency scanning)"""
        self._debug(f"Starting security analysis for repo: {self.repo_path}")
        
        result = {
            "scan_timestamp": datetime.utcnow().isoformat() + "Z",
            "package_manager": deps_info.get("package_manager"),
            "vulnerabilities": [],
            "summary": {
                "total": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0,
            },
            "scanners_used": [],
            "scan_method": None,
            "debug_logs": [],
        }
        
        package_manager = deps_info.get("package_manager")
        self._debug(f"Package manager detected: {package_manager}")
        self._debug("Running code security analysis (SAST) only - skipping dependency scanners")
        
        # Only run code security scanners (SAST), not dependency scanners
        # Try Snyk Code (code analysis) if available and token provided
        # Snyk Code works with multiple languages, so run it regardless of package manager
        if self.snyk_token:
            self._debug("Snyk token available, trying Snyk Code scanner...")
            try:
                snyk_result = self._run_snyk_code_test()
                if snyk_result:
                    vuln_count = len(snyk_result.get("vulnerabilities", []))
                    self._debug(f"Snyk Code found {vuln_count} vulnerabilities")
                    if "error" in snyk_result:
                        self._debug(f"Snyk Code error: {snyk_result['error']}")
                    result["vulnerabilities"].extend(snyk_result.get("vulnerabilities", []))
                    result["summary"] = self._calculate_summary(result["vulnerabilities"])
                    result["scanners_used"].append("snyk-code")
                    if not result["scan_method"]:
                        result["scan_method"] = "snyk-code"
                else:
                    self._debug("Snyk Code returned no results")
            except Exception as e:
                self._debug(f"Snyk Code failed with error: {str(e)}")
        else:
            self._debug("Snyk token not available, skipping Snyk Code")
        
        # Try SonarQube if configured
        self._debug("Checking for SonarQube...")
        try:
            sonar_result = self._run_sonarqube()
            if sonar_result:
                self._debug(f"SonarQube found results")
                result["vulnerabilities"].extend(sonar_result.get("vulnerabilities", []))
                result["summary"] = self._calculate_summary(result["vulnerabilities"])
                result["scanners_used"].append("sonarqube")
                if not result["scan_method"]:
                    result["scan_method"] = "sonarqube"
            else:
                self._debug("SonarQube not found")
        except Exception as e:
            self._debug(f"SonarQube check failed with error: {str(e)}")
        
        # Try CodeQL if available
        self._debug("Checking for CodeQL...")
        try:
            codeql_result = self._run_codeql()
            if codeql_result:
                self._debug(f"CodeQL found {len(codeql_result.get('vulnerabilities', []))} vulnerabilities")
                result["vulnerabilities"].extend(codeql_result.get("vulnerabilities", []))
                result["summary"] = self._calculate_summary(result["vulnerabilities"])
                result["scanners_used"].append("codeql")
                if not result["scan_method"]:
                    result["scan_method"] = "codeql"
            else:
                self._debug("CodeQL not found")
        except Exception as e:
            self._debug(f"CodeQL check failed with error: {str(e)}")
        
        # If no scanners found, mark as not scanned
        if not result["scanners_used"]:
            self._debug("No code security scanners were successful")
            result["scan_method"] = "none"
            result["note"] = "No code security scanners (SAST) available. Install and configure Snyk Code (requires SNYK_TOKEN), SonarQube, or CodeQL."
        
        result["summary"]["total"] = len(result["vulnerabilities"])
        result["debug_logs"] = self.debug_logs
        self._debug(f"Security analysis complete. Total vulnerabilities: {result['summary']['total']}")
        
        return result
    
    def _run_npm_audit(self) -> Optional[Dict[str, Any]]:
        """Run npm audit for Node.js dependencies"""
        package_json = self.repo_path / "package.json"
        self._debug(f"Checking for package.json at: {package_json}")
        if not package_json.exists():
            self._debug("package.json not found, skipping npm audit")
            return None
        
        try:
            self._debug("Running npm audit command...")
            # Try npm audit --json
            result = subprocess.run(
                ['npm', 'audit', '--json'],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.repo_path)
            )
            
            self._debug(f"npm audit exit code: {result.returncode}")
            
            if result.returncode == 0 or result.returncode == 1:  # Exit code 1 means vulnerabilities found
                self._debug("Parsing npm audit JSON output...")
                audit_data = json.loads(result.stdout)
                
                vulnerabilities = []
                if "vulnerabilities" in audit_data:
                    self._debug(f"Found {len(audit_data['vulnerabilities'])} vulnerability entries in npm audit output")
                    for pkg_name, vuln_info in audit_data["vulnerabilities"].items():
                        if isinstance(vuln_info, dict):
                            severity = vuln_info.get("severity", "unknown").lower()
                            if severity in ["critical", "high", "moderate", "low", "info"]:
                                vulnerabilities.append({
                                    "package": pkg_name,
                                    "severity": severity,
                                    "title": vuln_info.get("title", ""),
                                    "url": vuln_info.get("url", ""),
                                    "dependency_of": vuln_info.get("via", []),
                                    "vulnerable_versions": vuln_info.get("vulnerableVersions", ""),
                                    "patched_versions": vuln_info.get("patchedVersions", ""),
                                    "scanner": "npm-audit",
                                })
                else:
                    self._debug("No 'vulnerabilities' key in npm audit output")
                
                self._debug(f"npm audit found {len(vulnerabilities)} vulnerabilities")
                return {"vulnerabilities": vulnerabilities}
            else:
                self._debug(f"npm audit failed with exit code {result.returncode}")
                self._debug(f"npm audit stderr: {result.stderr[:500] if result.stderr else 'None'}")
        except FileNotFoundError:
            self._debug("npm command not found")
        except subprocess.TimeoutExpired:
            self._debug("npm audit timed out after 300 seconds")
        except json.JSONDecodeError as e:
            self._debug(f"Failed to parse npm audit JSON: {str(e)}")
            self._debug(f"npm audit stdout (first 500 chars): {result.stdout[:500] if 'result' in locals() else 'N/A'}")
        except Exception as e:
            self._debug(f"npm audit failed with exception: {type(e).__name__}: {str(e)}")
        
        return None
    
    def _run_snyk_code_test(self) -> Optional[Dict[str, Any]]:
        """Run Snyk Code test (SAST - Static Application Security Testing) on source code"""
        if not self.snyk_token:
            self._debug("Snyk token not provided, skipping Snyk Code")
            return None
        
        try:
            self._debug("Starting Snyk Code test...")
            # Set Snyk token as environment variable
            env = os.environ.copy()
            env['SNYK_TOKEN'] = self.snyk_token
            self._debug(f"Snyk token configured (length: {len(self.snyk_token)})")
            
            # Check if snyk command exists
            self._debug("Checking if snyk command is available...")
            check_result = subprocess.run(
                ['which', 'snyk'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if check_result.returncode != 0:
                self._debug("snyk command not found in PATH")
                return None
            self._debug(f"snyk command found at: {check_result.stdout.strip()}")
            
            # Run Snyk Code test - analyzes source code for vulnerabilities
            # Snyk Code supports: JavaScript, TypeScript, Python, Java, C#, Go, PHP, Ruby, etc.
            self._debug(f"Running snyk code test in directory: {self.repo_path}")
            self._debug("This may take up to 10 minutes (600 seconds timeout)...")
            
            result = subprocess.run(
                ['snyk', 'code', 'test', '--json'],
                capture_output=True,
                text=True,
                timeout=600,  # Code analysis can take longer
                env=env,
                cwd=str(self.repo_path)
            )
            
            self._debug(f"Snyk Code test completed with exit code: {result.returncode}")
            self._debug(f"Snyk Code stdout length: {len(result.stdout) if result.stdout else 0}")
            self._debug(f"Snyk Code stderr length: {len(result.stderr) if result.stderr else 0}")
            
            # Snyk returns exit code 1 when vulnerabilities are found (this is normal)
            if result.returncode == 0 or result.returncode == 1:
                self._debug("Parsing Snyk Code JSON output...")
                try:
                    snyk_data = json.loads(result.stdout)
                    self._debug("Successfully parsed JSON from stdout")
                except json.JSONDecodeError as e:
                    self._debug(f"Failed to parse JSON from stdout: {str(e)}")
                    self._debug(f"First 200 chars of stdout: {result.stdout[:200] if result.stdout else 'Empty'}")
                    # If stdout is not JSON, check stderr for JSON output
                    try:
                        self._debug("Trying to parse JSON from stderr...")
                        snyk_data = json.loads(result.stderr)
                        self._debug("Successfully parsed JSON from stderr")
                    except json.JSONDecodeError as e2:
                        self._debug(f"Failed to parse JSON from stderr: {str(e2)}")
                        self._debug(f"First 200 chars of stderr: {result.stderr[:200] if result.stderr else 'Empty'}")
                        return None
                
                vulnerabilities = []
                
                # Snyk Code JSON format
                if "runs" in snyk_data:
                    self._debug("Processing Snyk Code SARIF format...")
                    runs = snyk_data.get("runs", [])
                    self._debug(f"Found {len(runs)} runs in Snyk Code output")
                    # SARIF format (standard for Snyk Code)
                    for run in runs:
                        results = run.get("results", [])
                        self._debug(f"Processing {len(results)} results in run")
                        for result_item in results:
                            rule = result_item.get("rule", {})
                            message = result_item.get("message", {})
                            location = result_item.get("locations", [{}])[0].get("physicalLocation", {})
                            
                            # Extract file path
                            file_path = ""
                            if "artifactLocation" in location:
                                file_path = location["artifactLocation"].get("uri", "")
                            elif "fileLocation" in location:
                                file_path = location["fileLocation"].get("uri", "")
                            
                            # Extract line number
                            line_number = None
                            if "region" in location:
                                line_number = location["region"].get("startLine")
                            
                            # Get severity from rule properties or default
                            severity = "medium"
                            if "properties" in rule:
                                severity = rule["properties"].get("security-severity", "medium")
                            elif "severity" in rule:
                                severity = rule["severity"]
                            
                            vulnerabilities.append({
                                "rule_id": rule.get("id", ""),
                                "severity": self._map_snyk_severity(severity),
                                "title": rule.get("shortDescription", {}).get("text", ""),
                                "message": message.get("text", ""),
                                "file": file_path,
                                "line": line_number,
                                "url": rule.get("helpUri", ""),
                                "scanner": "snyk-code",
                                "type": "code"  # Indicates this is code analysis, not dependency
                            })
                elif "vulnerabilities" in snyk_data:
                    self._debug("Processing Snyk Code alternative format...")
                    vulns = snyk_data["vulnerabilities"]
                    self._debug(f"Found {len(vulns)} vulnerabilities in alternative format")
                    # Alternative format
                    for vuln in vulns:
                        vulnerabilities.append({
                            "rule_id": vuln.get("id", ""),
                            "severity": vuln.get("severity", "unknown").lower(),
                            "title": vuln.get("title", ""),
                            "message": vuln.get("message", ""),
                            "file": vuln.get("file", ""),
                            "line": vuln.get("line"),
                            "scanner": "snyk-code",
                            "type": "code"
                        })
                else:
                    self._debug(f"Snyk Code output format not recognized. Keys found: {list(snyk_data.keys())[:10]}")
                
                self._debug(f"Snyk Code found {len(vulnerabilities)} vulnerabilities")
                return {"vulnerabilities": vulnerabilities}
        except FileNotFoundError:
            # Snyk CLI not installed
            self._debug("snyk command not found")
            return None
        except subprocess.TimeoutExpired:
            self._debug("Snyk Code test timed out after 600 seconds")
            return {
                "vulnerabilities": [],
                "error": "Snyk Code scan timed out after 10 minutes"
            }
        except json.JSONDecodeError as e:
            self._debug(f"Failed to parse Snyk Code JSON: {str(e)}")
            return {
                "vulnerabilities": [],
                "error": f"Snyk Code JSON parse failed: {str(e)}"
            }
        except Exception as e:
            # Log error but don't fail completely
            self._debug(f"Snyk Code scan failed with exception: {type(e).__name__}: {str(e)}")
            import traceback
            self._debug(f"Traceback: {traceback.format_exc()}")
            return {
                "vulnerabilities": [],
                "error": f"Snyk Code scan failed: {str(e)}"
            }
        
        return None
    
    def _map_snyk_severity(self, severity: str) -> str:
        """Map Snyk severity to standard format"""
        severity_map = {
            "error": "high",
            "warning": "medium",
            "note": "low",
        }
        return severity_map.get(severity.lower(), severity.lower())
    
    def _run_safety_check(self) -> Optional[Dict[str, Any]]:
        """Run safety check for Python dependencies"""
        try:
            self._debug("Running safety check...")
            result = subprocess.run(
                ['safety', 'check', '--json'],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.repo_path)
            )
            
            self._debug(f"safety exit code: {result.returncode}")
            
            if result.returncode == 0 or result.returncode == 1:
                self._debug("Parsing safety JSON output...")
                safety_data = json.loads(result.stdout)
                
                vulnerabilities = []
                if isinstance(safety_data, list):
                    self._debug(f"safety found {len(safety_data)} vulnerabilities")
                    for vuln in safety_data:
                        vulnerabilities.append({
                            "package": vuln.get("package", ""),
                            "installed_version": vuln.get("installed_version", ""),
                            "vulnerable_spec": vuln.get("vulnerable_spec", ""),
                            "severity": self._map_safety_severity(vuln.get("advisory", "")),
                            "advisory": vuln.get("advisory", ""),
                            "scanner": "safety",
                        })
                
                return {"vulnerabilities": vulnerabilities}
            else:
                self._debug(f"safety failed with exit code {result.returncode}")
                self._debug(f"safety stderr: {result.stderr[:500] if result.stderr else 'None'}")
        except FileNotFoundError:
            self._debug("safety command not found")
        except subprocess.TimeoutExpired:
            self._debug("safety timed out after 300 seconds")
        except json.JSONDecodeError as e:
            self._debug(f"Failed to parse safety JSON: {str(e)}")
            self._debug(f"safety stdout (first 500 chars): {result.stdout[:500] if 'result' in locals() else 'N/A'}")
        except Exception as e:
            self._debug(f"safety failed with exception: {type(e).__name__}: {str(e)}")
        
        return None
    
    def _run_pip_audit(self) -> Optional[Dict[str, Any]]:
        """Run pip-audit for Python dependencies"""
        try:
            self._debug("Running pip-audit...")
            result = subprocess.run(
                ['pip-audit', '--format=json'],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.repo_path)
            )
            
            self._debug(f"pip-audit exit code: {result.returncode}")
            
            if result.returncode == 0 or result.returncode == 1:
                self._debug("Parsing pip-audit JSON output...")
                audit_data = json.loads(result.stdout)
                
                vulnerabilities = []
                if "vulnerabilities" in audit_data:
                    self._debug(f"pip-audit found {len(audit_data['vulnerabilities'])} vulnerabilities")
                    for vuln in audit_data["vulnerabilities"]:
                        vulnerabilities.append({
                            "package": vuln.get("name", ""),
                            "installed_version": vuln.get("installed_version", ""),
                            "vulnerable_spec": vuln.get("vulnerable_spec", ""),
                            "severity": self._map_cvss_severity(vuln.get("cvss", {}).get("score", 0)),
                            "cve": vuln.get("id", ""),
                            "cvss_score": vuln.get("cvss", {}).get("score", 0),
                            "scanner": "pip-audit",
                        })
                else:
                    self._debug("No 'vulnerabilities' key in pip-audit output")
                
                return {"vulnerabilities": vulnerabilities}
            else:
                self._debug(f"pip-audit failed with exit code {result.returncode}")
                self._debug(f"pip-audit stderr: {result.stderr[:500] if result.stderr else 'None'}")
        except FileNotFoundError:
            self._debug("pip-audit command not found")
        except subprocess.TimeoutExpired:
            self._debug("pip-audit timed out after 300 seconds")
        except json.JSONDecodeError as e:
            self._debug(f"Failed to parse pip-audit JSON: {str(e)}")
            self._debug(f"pip-audit stdout (first 500 chars): {result.stdout[:500] if 'result' in locals() else 'N/A'}")
        except Exception as e:
            self._debug(f"pip-audit failed with exception: {type(e).__name__}: {str(e)}")
        
        return None
    
    def _run_sonarqube(self) -> Optional[Dict[str, Any]]:
        """Check for SonarQube results if available"""
        # SonarQube typically runs in CI/CD and produces reports
        # Look for common report locations
        self._debug("Checking for SonarQube reports...")
        sonar_reports = [
            self.repo_path / ".scannerwork" / "report-task.txt",
            self.repo_path / "sonar-report.json",
            self.repo_path / "target" / "sonar" / "report-task.txt",
        ]
        
        for report_path in sonar_reports:
            self._debug(f"Checking for SonarQube report at: {report_path}")
            if report_path.exists():
                self._debug(f"Found SonarQube report at: {report_path}")
                try:
                    # SonarQube integration would require API access
                    # For now, return a placeholder
                    return {
                        "vulnerabilities": [],
                        "note": "SonarQube report found but requires API integration for full analysis"
                    }
                except Exception as e:
                    self._debug(f"Error reading SonarQube report: {str(e)}")
                    pass
        
        self._debug("No SonarQube reports found")
        return None
    
    def _run_codeql(self) -> Optional[Dict[str, Any]]:
        """Check for CodeQL results if available"""
        # CodeQL typically runs in GitHub Actions
        self._debug("Checking for CodeQL results...")
        codeql_results = [
            self.repo_path / ".github" / "codeql" / "results",
            self.repo_path / "codeql-results.json",
        ]
        
        for result_path in codeql_results:
            self._debug(f"Checking for CodeQL results at: {result_path}")
            if result_path.exists():
                self._debug(f"Found CodeQL results at: {result_path}")
                try:
                    if result_path.is_file():
                        self._debug("Reading CodeQL results file...")
                        with open(result_path, 'r') as f:
                            codeql_data = json.load(f)
                            # Parse CodeQL results format
                            vulnerabilities = []
                            if "runs" in codeql_data:
                                self._debug(f"Found {len(codeql_data['runs'])} runs in CodeQL results")
                                for run in codeql_data["runs"]:
                                    if "results" in run:
                                        results_count = len(run["results"])
                                        self._debug(f"Processing {results_count} results in CodeQL run")
                                        for result in run["results"]:
                                            rule = result.get("rule", {})
                                            severity = rule.get("severity", "unknown").lower()
                                            vulnerabilities.append({
                                                "rule_id": rule.get("id", ""),
                                                "severity": severity,
                                                "message": result.get("message", {}).get("text", ""),
                                                "location": result.get("locations", [{}])[0].get("physicalLocation", {}),
                                                "scanner": "codeql",
                                            })
                                self._debug(f"CodeQL found {len(vulnerabilities)} vulnerabilities")
                            return {"vulnerabilities": vulnerabilities}
                except json.JSONDecodeError as e:
                    self._debug(f"Failed to parse CodeQL JSON: {str(e)}")
                except Exception as e:
                    self._debug(f"Error reading CodeQL results: {type(e).__name__}: {str(e)}")
        
        self._debug("No CodeQL results found")
        return None
    
    def _calculate_summary(self, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate summary of vulnerabilities by severity"""
        summary = {
            "total": len(vulnerabilities),
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
        
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "unknown").lower()
            if severity == "critical":
                summary["critical"] += 1
            elif severity == "high":
                summary["high"] += 1
            elif severity in ["medium", "moderate"]:
                summary["medium"] += 1
            elif severity == "low":
                summary["low"] += 1
            elif severity == "info":
                summary["info"] += 1
        
        return summary
    
    def _map_safety_severity(self, advisory: str) -> str:
        """Map safety advisory to severity"""
        # Safety doesn't always provide severity, default to medium
        return "medium"
    
    def _map_cvss_severity(self, cvss_score: float) -> str:
        """Map CVSS score to severity"""
        if cvss_score >= 9.0:
            return "critical"
        elif cvss_score >= 7.0:
            return "high"
        elif cvss_score >= 4.0:
            return "medium"
        elif cvss_score >= 0.1:
            return "low"
        else:
            return "info"

