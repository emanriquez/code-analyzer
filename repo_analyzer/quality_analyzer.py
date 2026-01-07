"""Quality analysis module for test execution and coverage"""

import json
import subprocess
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class QualityAnalyzer:
    """Analyzes test results and code coverage"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
    
    def analyze(self, stack_info: Dict[str, Any]) -> Dict[str, Any]:
        """Run tests and collect coverage"""
        result = {
            "test_results": None,
            "coverage": None,
            "test_framework": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        primary_lang = stack_info.get("primary_language", "").lower()
        frameworks = [f.lower() for f in stack_info.get("frameworks", [])]
        
        # Detect and run tests based on stack
        if primary_lang == "javascript" or "node" in primary_lang:
            # Try Jest first (most common for React/Node)
            jest_result = self._run_jest()
            if jest_result:
                result["test_results"] = jest_result
                result["test_framework"] = "jest"
                result["coverage"] = self._parse_jest_coverage()
            
            # Try Mocha if Jest didn't work
            if not result["test_results"]:
                mocha_result = self._run_mocha()
                if mocha_result:
                    result["test_results"] = mocha_result
                    result["test_framework"] = "mocha"
            
            # Try Vitest
            if not result["test_results"]:
                vitest_result = self._run_vitest()
                if vitest_result:
                    result["test_results"] = vitest_result
                    result["test_framework"] = "vitest"
                    result["coverage"] = self._parse_vitest_coverage()
        
        elif primary_lang == "python":
            # Try pytest first (most common)
            pytest_result = self._run_pytest()
            if pytest_result:
                result["test_results"] = pytest_result
                result["test_framework"] = "pytest"
                result["coverage"] = self._parse_pytest_coverage()
            
            # Try unittest if pytest didn't work
            if not result["test_results"]:
                unittest_result = self._run_unittest()
                if unittest_result:
                    result["test_results"] = unittest_result
                    result["test_framework"] = "unittest"
        
        # Try to find existing coverage reports
        if not result["coverage"]:
            result["coverage"] = self._find_existing_coverage()
        
        # If no tests were run, return empty structure
        if not result["test_results"]:
            result["test_results"] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0,
                "note": "No test framework detected or tests not configured"
            }
        
        return result
    
    def _run_jest(self) -> Optional[Dict[str, Any]]:
        """Run Jest tests"""
        package_json = self.repo_path / "package.json"
        if not package_json.exists():
            return None
        
        try:
            with open(package_json, 'r') as f:
                pkg_data = json.load(f)
                scripts = pkg_data.get("scripts", {})
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                
                # Check if Jest is available
                if "jest" not in deps and "test" not in scripts:
                    return None
        except Exception:
            return None
        
        try:
            # Try to run Jest
            result = subprocess.run(
                ['npm', 'test', '--', '--json', '--no-coverage'],
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(self.repo_path)
            )
            
            if result.returncode == 0 or result.returncode == 1:  # Jest returns 1 if tests fail
                try:
                    jest_data = json.loads(result.stdout)
                    return {
                        "total": jest_data.get("numTotalTests", 0),
                        "passed": jest_data.get("numPassedTests", 0),
                        "failed": jest_data.get("numFailedTests", 0),
                        "skipped": jest_data.get("numPendingTests", 0),
                        "duration": jest_data.get("startTime", 0),
                        "test_files": jest_data.get("testResults", []),
                    }
                except json.JSONDecodeError:
                    # Try parsing from stderr or different format
                    pass
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
        
        return None
    
    def _run_mocha(self) -> Optional[Dict[str, Any]]:
        """Run Mocha tests"""
        package_json = self.repo_path / "package.json"
        if not package_json.exists():
            return None
        
        try:
            with open(package_json, 'r') as f:
                pkg_data = json.load(f)
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                
                if "mocha" not in deps:
                    return None
        except Exception:
            return None
        
        try:
            result = subprocess.run(
                ['npm', 'test', '--', '--reporter', 'json'],
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(self.repo_path)
            )
            
            if result.returncode == 0 or result.returncode == 1:
                try:
                    mocha_data = json.loads(result.stdout)
                    total = len(mocha_data.get("tests", []))
                    passed = sum(1 for t in mocha_data.get("tests", []) if t.get("err") is None)
                    failed = total - passed
                    
                    return {
                        "total": total,
                        "passed": passed,
                        "failed": failed,
                        "skipped": 0,
                        "duration": mocha_data.get("duration", 0),
                    }
                except json.JSONDecodeError:
                    pass
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
        
        return None
    
    def _run_vitest(self) -> Optional[Dict[str, Any]]:
        """Run Vitest tests"""
        package_json = self.repo_path / "package.json"
        if not package_json.exists():
            return None
        
        try:
            with open(package_json, 'r') as f:
                pkg_data = json.load(f)
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                
                if "vitest" not in deps:
                    return None
        except Exception:
            return None
        
        try:
            result = subprocess.run(
                ['npm', 'test', '--', '--reporter=json'],
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(self.repo_path)
            )
            
            if result.returncode == 0 or result.returncode == 1:
                try:
                    vitest_data = json.loads(result.stdout)
                    return {
                        "total": vitest_data.get("numTotalTests", 0),
                        "passed": vitest_data.get("numPassedTests", 0),
                        "failed": vitest_data.get("numFailedTests", 0),
                        "skipped": vitest_data.get("numPendingTests", 0),
                        "duration": vitest_data.get("duration", 0),
                    }
                except json.JSONDecodeError:
                    pass
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
        
        return None
    
    def _run_pytest(self) -> Optional[Dict[str, Any]]:
        """Run pytest tests"""
        try:
            # Check if pytest is available
            result = subprocess.run(
                ['pytest', '--version'],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.repo_path)
            )
            
            if result.returncode != 0:
                return None
        except FileNotFoundError:
            return None
        
        try:
            # Run pytest with JSON report
            result = subprocess.run(
                ['pytest', '--json-report', '--json-report-file=pytest-report.json', '-v'],
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(self.repo_path)
            )
            
            # Try to read the JSON report
            report_file = self.repo_path / "pytest-report.json"
            if report_file.exists():
                try:
                    with open(report_file, 'r') as f:
                        pytest_data = json.load(f)
                        return {
                            "total": pytest_data.get("summary", {}).get("total", 0),
                            "passed": pytest_data.get("summary", {}).get("passed", 0),
                            "failed": pytest_data.get("summary", {}).get("failed", 0),
                            "skipped": pytest_data.get("summary", {}).get("skipped", 0),
                            "duration": pytest_data.get("duration", 0),
                        }
                except Exception:
                    pass
            
            # Fallback: parse from stdout
            if result.returncode == 0 or result.returncode == 1:
                # Parse pytest output
                lines = result.stdout.split('\n')
                total = 0
                passed = 0
                failed = 0
                
                for line in lines:
                    if 'passed' in line.lower() and 'failed' in line.lower():
                        # Format: "X passed, Y failed in Zs"
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'passed':
                                passed = int(parts[i-1]) if i > 0 else 0
                            elif part == 'failed':
                                failed = int(parts[i-1]) if i > 0 else 0
                        total = passed + failed
                        break
                
                if total > 0:
                    return {
                        "total": total,
                        "passed": passed,
                        "failed": failed,
                        "skipped": 0,
                        "duration": 0,
                    }
        except (subprocess.TimeoutExpired, Exception):
            pass
        
        return None
    
    def _run_unittest(self) -> Optional[Dict[str, Any]]:
        """Run Python unittest"""
        try:
            result = subprocess.run(
                ['python', '-m', 'unittest', 'discover', '-v'],
                capture_output=True,
                text=True,
                timeout=600,
                cwd=str(self.repo_path)
            )
            
            if result.returncode == 0 or result.returncode == 1:
                # Parse unittest output
                lines = result.stdout.split('\n')
                total = 0
                passed = 0
                failed = 0
                
                for line in lines:
                    if 'Ran' in line and 'test' in line:
                        # Format: "Ran X tests in Ys"
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'tests' and i > 0:
                                total = int(parts[i-1]) if parts[i-1].isdigit() else 0
                    if 'OK' in line:
                        passed = total
                    if 'FAILED' in line:
                        failed = total - passed
                
                if total > 0:
                    return {
                        "total": total,
                        "passed": passed,
                        "failed": failed,
                        "skipped": 0,
                        "duration": 0,
                    }
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
        
        return None
    
    def _parse_jest_coverage(self) -> Optional[Dict[str, Any]]:
        """Parse Jest coverage report"""
        coverage_paths = [
            self.repo_path / "coverage" / "coverage-summary.json",
            self.repo_path / "coverage-summary.json",
        ]
        
        for path in coverage_paths:
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        coverage_data = json.load(f)
                        total = coverage_data.get("total", {})
                        return {
                            "lines": total.get("lines", {}).get("pct", 0),
                            "statements": total.get("statements", {}).get("pct", 0),
                            "functions": total.get("functions", {}).get("pct", 0),
                            "branches": total.get("branches", {}).get("pct", 0),
                        }
                except Exception:
                    pass
        
        return None
    
    def _parse_vitest_coverage(self) -> Optional[Dict[str, Any]]:
        """Parse Vitest coverage report"""
        # Vitest uses similar format to Jest
        return self._parse_jest_coverage()
    
    def _parse_pytest_coverage(self) -> Optional[Dict[str, Any]]:
        """Parse pytest-cov coverage report"""
        coverage_paths = [
            self.repo_path / ".coverage",
            self.repo_path / "htmlcov" / "index.html",
            self.repo_path / "coverage.xml",
        ]
        
        # Try to read coverage.xml (Cobertura format)
        xml_path = self.repo_path / "coverage.xml"
        if xml_path.exists():
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                
                # Cobertura XML format
                line_rate = float(root.get("line-rate", 0)) * 100
                branch_rate = float(root.get("branch-rate", 0)) * 100
                
                return {
                    "lines": line_rate,
                    "branches": branch_rate,
                    "statements": line_rate,  # Approximate
                    "functions": line_rate,  # Approximate
                }
            except Exception:
                pass
        
        # Try to run coverage report command
        try:
            result = subprocess.run(
                ['coverage', 'report', '--format=json'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.repo_path)
            )
            
            if result.returncode == 0:
                try:
                    coverage_data = json.loads(result.stdout)
                    totals = coverage_data.get("totals", {})
                    return {
                        "lines": totals.get("percent_covered", 0),
                        "statements": totals.get("percent_covered", 0),
                        "functions": totals.get("percent_covered", 0),
                        "branches": totals.get("percent_covered", 0),
                    }
                except json.JSONDecodeError:
                    pass
        except (FileNotFoundError, Exception):
            pass
        
        return None
    
    def _find_existing_coverage(self) -> Optional[Dict[str, Any]]:
        """Try to find existing coverage reports from various tools"""
        # Try Jest/Vitest format
        coverage = self._parse_jest_coverage()
        if coverage:
            return coverage
        
        # Try pytest format
        coverage = self._parse_pytest_coverage()
        if coverage:
            return coverage
        
        # Try Istanbul/NYC (Node.js)
        nyc_path = self.repo_path / ".nyc_output" / "coverage.json"
        if nyc_path.exists():
            try:
                with open(nyc_path, 'r') as f:
                    nyc_data = json.load(f)
                    # Parse NYC format
                    return {
                        "lines": 0,  # Would need to calculate
                        "statements": 0,
                        "functions": 0,
                        "branches": 0,
                        "note": "NYC coverage found but parsing not fully implemented"
                    }
            except Exception:
                pass
        
        return None

