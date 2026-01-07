"""Security analysis module for code and dependency vulnerability scanning"""

import json
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests


class SecurityAnalyzer:
    """Analyzes security vulnerabilities in dependencies"""
    
    def __init__(self, repo_path: str, snyk_token: Optional[str] = None):
        self.repo_path = Path(repo_path)
        self.snyk_token = snyk_token or os.environ.get('SNYK_TOKEN')
    
    def analyze(self, deps_info: Dict[str, Any], stack_info: Dict[str, Any]) -> Dict[str, Any]:
        """Perform security analysis"""
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
        }
        
        package_manager = deps_info.get("package_manager")
        
        # Try different scanners based on package manager
        if package_manager in ["npm", "yarn", "pnpm"]:
            # Try npm audit first
            npm_result = self._run_npm_audit()
            if npm_result:
                result["vulnerabilities"].extend(npm_result.get("vulnerabilities", []))
                result["summary"] = self._calculate_summary(result["vulnerabilities"])
                result["scanners_used"].append("npm-audit")
                result["scan_method"] = "npm-audit"
            
        # Try Snyk Code (code analysis) if available and token provided
        # Snyk Code works with multiple languages, so run it regardless of package manager
        if self.snyk_token:
            snyk_result = self._run_snyk_code_test()
            if snyk_result:
                result["vulnerabilities"].extend(snyk_result.get("vulnerabilities", []))
                result["summary"] = self._calculate_summary(result["vulnerabilities"])
                result["scanners_used"].append("snyk-code")
                if not result["scan_method"]:
                    result["scan_method"] = "snyk-code"
        
        if package_manager in ["npm", "yarn", "pnpm"]:
            # Try npm audit for dependencies
            npm_result = self._run_npm_audit()
            if npm_result:
                result["vulnerabilities"].extend(npm_result.get("vulnerabilities", []))
                result["summary"] = self._calculate_summary(result["vulnerabilities"])
                result["scanners_used"].append("npm-audit")
                if not result["scan_method"]:
                    result["scan_method"] = "npm-audit"
        
        elif package_manager in ["pip", "pipenv", "poetry"]:
            # Try safety for Python
            safety_result = self._run_safety_check()
            if safety_result:
                result["vulnerabilities"].extend(safety_result.get("vulnerabilities", []))
                result["summary"] = self._calculate_summary(result["vulnerabilities"])
                result["scanners_used"].append("safety")
                result["scan_method"] = "safety"
            
            # Try pip-audit if available
            pip_audit_result = self._run_pip_audit()
            if pip_audit_result:
                result["vulnerabilities"].extend(pip_audit_result.get("vulnerabilities", []))
                result["summary"] = self._calculate_summary(result["vulnerabilities"])
                result["scanners_used"].append("pip-audit")
                if not result["scan_method"]:
                    result["scan_method"] = "pip-audit"
        
        # Try SonarQube if configured
        sonar_result = self._run_sonarqube()
        if sonar_result:
            result["vulnerabilities"].extend(sonar_result.get("vulnerabilities", []))
            result["summary"] = self._calculate_summary(result["vulnerabilities"])
            result["scanners_used"].append("sonarqube")
            if not result["scan_method"]:
                result["scan_method"] = "sonarqube"
        
        # Try CodeQL if available
        codeql_result = self._run_codeql()
        if codeql_result:
            result["vulnerabilities"].extend(codeql_result.get("vulnerabilities", []))
            result["summary"] = self._calculate_summary(result["vulnerabilities"])
            result["scanners_used"].append("codeql")
            if not result["scan_method"]:
                result["scan_method"] = "codeql"
        
        # If no scanners found, mark as not scanned
        if not result["scanners_used"]:
            result["scan_method"] = "none"
            result["note"] = "No security scanners available. Install npm/yarn for Node.js or safety/pip-audit for Python."
        
        result["summary"]["total"] = len(result["vulnerabilities"])
        
        return result
    
    def _run_npm_audit(self) -> Optional[Dict[str, Any]]:
        """Run npm audit for Node.js dependencies"""
        package_json = self.repo_path / "package.json"
        if not package_json.exists():
            return None
        
        try:
            # Try npm audit --json
            result = subprocess.run(
                ['npm', 'audit', '--json'],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.repo_path)
            )
            
            if result.returncode == 0 or result.returncode == 1:  # Exit code 1 means vulnerabilities found
                audit_data = json.loads(result.stdout)
                
                vulnerabilities = []
                if "vulnerabilities" in audit_data:
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
                
                return {"vulnerabilities": vulnerabilities}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
            pass
        
        return None
    
    def _run_snyk_code_test(self) -> Optional[Dict[str, Any]]:
        """Run Snyk Code test (SAST - Static Application Security Testing) on source code"""
        if not self.snyk_token:
            return None
        
        try:
            # Set Snyk token as environment variable
            env = os.environ.copy()
            env['SNYK_TOKEN'] = self.snyk_token
            
            # Run Snyk Code test - analyzes source code for vulnerabilities
            # Snyk Code supports: JavaScript, TypeScript, Python, Java, C#, Go, PHP, Ruby, etc.
            result = subprocess.run(
                ['snyk', 'code', 'test', '--json'],
                capture_output=True,
                text=True,
                timeout=600,  # Code analysis can take longer
                env=env,
                cwd=str(self.repo_path)
            )
            
            # Snyk returns exit code 1 when vulnerabilities are found (this is normal)
            if result.returncode == 0 or result.returncode == 1:
                try:
                    snyk_data = json.loads(result.stdout)
                except json.JSONDecodeError:
                    # If stdout is not JSON, check stderr for JSON output
                    try:
                        snyk_data = json.loads(result.stderr)
                    except json.JSONDecodeError:
                        return None
                
                vulnerabilities = []
                
                # Snyk Code JSON format
                if "runs" in snyk_data:
                    # SARIF format (standard for Snyk Code)
                    for run in snyk_data.get("runs", []):
                        for result_item in run.get("results", []):
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
                    # Alternative format
                    for vuln in snyk_data["vulnerabilities"]:
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
                
                return {"vulnerabilities": vulnerabilities}
        except FileNotFoundError:
            # Snyk CLI not installed
            return None
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            # Log error but don't fail completely
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
            result = subprocess.run(
                ['safety', 'check', '--json'],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.repo_path)
            )
            
            if result.returncode == 0 or result.returncode == 1:
                safety_data = json.loads(result.stdout)
                
                vulnerabilities = []
                if isinstance(safety_data, list):
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
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
            pass
        
        return None
    
    def _run_pip_audit(self) -> Optional[Dict[str, Any]]:
        """Run pip-audit for Python dependencies"""
        try:
            result = subprocess.run(
                ['pip-audit', '--format=json'],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.repo_path)
            )
            
            if result.returncode == 0 or result.returncode == 1:
                audit_data = json.loads(result.stdout)
                
                vulnerabilities = []
                if "vulnerabilities" in audit_data:
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
                
                return {"vulnerabilities": vulnerabilities}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
            pass
        
        return None
    
    def _run_sonarqube(self) -> Optional[Dict[str, Any]]:
        """Check for SonarQube results if available"""
        # SonarQube typically runs in CI/CD and produces reports
        # Look for common report locations
        sonar_reports = [
            self.repo_path / ".scannerwork" / "report-task.txt",
            self.repo_path / "sonar-report.json",
            self.repo_path / "target" / "sonar" / "report-task.txt",
        ]
        
        for report_path in sonar_reports:
            if report_path.exists():
                try:
                    # SonarQube integration would require API access
                    # For now, return a placeholder
                    return {
                        "vulnerabilities": [],
                        "note": "SonarQube report found but requires API integration for full analysis"
                    }
                except Exception:
                    pass
        
        return None
    
    def _run_codeql(self) -> Optional[Dict[str, Any]]:
        """Check for CodeQL results if available"""
        # CodeQL typically runs in GitHub Actions
        codeql_results = [
            self.repo_path / ".github" / "codeql" / "results",
            self.repo_path / "codeql-results.json",
        ]
        
        for result_path in codeql_results:
            if result_path.exists():
                try:
                    if result_path.is_file():
                        with open(result_path, 'r') as f:
                            codeql_data = json.load(f)
                            # Parse CodeQL results format
                            vulnerabilities = []
                            if "runs" in codeql_data:
                                for run in codeql_data["runs"]:
                                    if "results" in run:
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
                            return {"vulnerabilities": vulnerabilities}
                except Exception:
                    pass
        
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

