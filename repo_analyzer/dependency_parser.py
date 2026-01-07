"""Dependency parsing module"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml


class DependencyParser:
    """Parses dependencies from various package manager files"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
    
    def parse(self) -> Dict[str, Any]:
        """Parse all dependencies from the repository"""
        result = {
            "dependencies": [],
            "dev_dependencies": [],
            "package_manager": None,
            "lockfile_present": False,
            "total_dependencies": 0,
            "vulnerabilities": []  # Placeholder for future SCA integration
        }
        
        # Try Node.js ecosystem first
        node_deps = self._parse_node_dependencies()
        if node_deps:
            result.update(node_deps)
            return result
        
        # Try Python ecosystem
        python_deps = self._parse_python_dependencies()
        if python_deps:
            result.update(python_deps)
            return result
        
        return result
    
    def _parse_node_dependencies(self) -> Optional[Dict[str, Any]]:
        """Parse Node.js dependencies from package.json and lockfiles"""
        package_json = self.repo_path / "package.json"
        
        if not package_json.exists():
            return None
        
        try:
            with open(package_json, 'r', encoding='utf-8') as f:
                pkg_data = json.load(f)
            
            deps = pkg_data.get("dependencies", {})
            dev_deps = pkg_data.get("devDependencies", {})
            peer_deps = pkg_data.get("peerDependencies", {})
            optional_deps = pkg_data.get("optionalDependencies", {})
            
            # Determine package manager from lockfile
            package_manager = None
            lockfile_present = False
            
            if (self.repo_path / "pnpm-lock.yaml").exists():
                package_manager = "pnpm"
                lockfile_present = True
            elif (self.repo_path / "yarn.lock").exists():
                package_manager = "yarn"
                lockfile_present = True
            elif (self.repo_path / "package-lock.json").exists():
                package_manager = "npm"
                lockfile_present = True
            else:
                package_manager = "npm"  # Default if package.json exists
            
            # Format dependencies
            dependencies = [
                {"name": name, "version": version, "type": "runtime"}
                for name, version in deps.items()
            ]
            
            dev_dependencies = [
                {"name": name, "version": version, "type": "dev"}
                for name, version in dev_deps.items()
            ]
            
            peer_dependencies = [
                {"name": name, "version": version, "type": "peer"}
                for name, version in peer_deps.items()
            ]
            
            optional_dependencies_list = [
                {"name": name, "version": version, "type": "optional"}
                for name, version in optional_deps.items()
            ]
            
            # Parse lockfile for exact versions (if available)
            lockfile_info = self._parse_lockfile(package_manager)
            
            return {
                "package_manager": package_manager,
                "lockfile_present": lockfile_present,
                "lockfile_info": lockfile_info,
                "dependencies": dependencies,
                "dev_dependencies": dev_dependencies,
                "peer_dependencies": peer_dependencies,
                "optional_dependencies": optional_dependencies_list,
                "total_dependencies": len(deps) + len(dev_deps) + len(peer_deps) + len(optional_deps),
                "package_json": {
                    "name": pkg_data.get("name"),
                    "version": pkg_data.get("version"),
                    "description": pkg_data.get("description"),
                    "scripts": pkg_data.get("scripts", {}),
                    "engines": pkg_data.get("engines", {}),
                }
            }
        except Exception as e:
            return {
                "error": f"Failed to parse package.json: {str(e)}",
                "package_manager": "unknown"
            }
    
    def _parse_lockfile(self, package_manager: str) -> Dict[str, Any]:
        """Parse lockfile for exact dependency versions"""
        lockfile_info = {
            "type": package_manager,
            "resolved_versions": {},
            "integrity_hashes": {}
        }
        
        try:
            if package_manager == "npm" and (self.repo_path / "package-lock.json").exists():
                with open(self.repo_path / "package-lock.json", 'r', encoding='utf-8') as f:
                    lock_data = json.load(f)
                    lockfile_info["lockfile_version"] = lock_data.get("lockfileVersion")
                    lockfile_info["npm_version"] = lock_data.get("npmVersion")
                    # Extract resolved versions from dependencies tree
                    if "packages" in lock_data:
                        for pkg_path, pkg_info in lock_data["packages"].items():
                            if pkg_path and "version" in pkg_info:
                                lockfile_info["resolved_versions"][pkg_path] = pkg_info["version"]
            
            elif package_manager == "yarn" and (self.repo_path / "yarn.lock").exists():
                # Yarn lockfile is in a custom format, basic parsing
                lockfile_info["format"] = "yarn-v1"
                # Full parsing would require a yarn.lock parser library
            
            elif package_manager == "pnpm" and (self.repo_path / "pnpm-lock.yaml").exists():
                with open(self.repo_path / "pnpm-lock.yaml", 'r', encoding='utf-8') as f:
                    lock_data = yaml.safe_load(f)
                    lockfile_info["lockfile_version"] = lock_data.get("lockfileVersion")
                    if "packages" in lock_data:
                        for pkg_path, pkg_info in lock_data["packages"].items():
                            if isinstance(pkg_info, dict) and "version" in pkg_info:
                                lockfile_info["resolved_versions"][pkg_path] = pkg_info["version"]
        except Exception as e:
            lockfile_info["error"] = f"Failed to parse lockfile: {str(e)}"
        
        return lockfile_info
    
    def _parse_python_dependencies(self) -> Optional[Dict[str, Any]]:
        """Parse Python dependencies from requirements.txt, pyproject.toml, etc."""
        dependencies = []
        dev_dependencies = []
        package_manager = None
        lockfile_present = False
        
        # Try requirements.txt
        req_txt = self.repo_path / "requirements.txt"
        if req_txt.exists():
            package_manager = "pip"
            try:
                with open(req_txt, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Parse package spec (name==version, name>=version, etc.)
                            if '==' in line:
                                name, version = line.split('==', 1)
                                dependencies.append({
                                    "name": name.strip(),
                                    "version": version.strip(),
                                    "type": "runtime",
                                    "spec": line
                                })
                            elif '>=' in line:
                                name, version = line.split('>=', 1)
                                dependencies.append({
                                    "name": name.strip(),
                                    "version": f">={version.strip()}",
                                    "type": "runtime",
                                    "spec": line
                                })
                            else:
                                dependencies.append({
                                    "name": line,
                                    "version": None,
                                    "type": "runtime",
                                    "spec": line
                                })
            except Exception as e:
                return {"error": f"Failed to parse requirements.txt: {str(e)}"}
        
        # Try requirements-dev.txt
        req_dev_txt = self.repo_path / "requirements-dev.txt"
        if req_dev_txt.exists():
            try:
                with open(req_dev_txt, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '==' in line:
                                name, version = line.split('==', 1)
                                dev_dependencies.append({
                                    "name": name.strip(),
                                    "version": version.strip(),
                                    "type": "dev",
                                    "spec": line
                                })
                            else:
                                dev_dependencies.append({
                                    "name": line,
                                    "version": None,
                                    "type": "dev",
                                    "spec": line
                                })
            except Exception:
                pass
        
        # Try pyproject.toml
        pyproject = self.repo_path / "pyproject.toml"
        if pyproject.exists():
            try:
                # Try Python 3.11+ built-in tomllib first
                try:
                    import tomllib
                    with open(pyproject, 'rb') as f:
                        pyproject_data = tomllib.load(f)
                except ImportError:
                    # Fallback to tomli for older Python versions
                    import tomli
                    with open(pyproject, 'rb') as f:
                        pyproject_data = tomli.load(f)
                    
                if "project" in pyproject_data and "dependencies" in pyproject_data["project"]:
                    for dep in pyproject_data["project"]["dependencies"]:
                        dependencies.append({
                            "name": dep.split()[0] if ' ' in dep else dep,
                            "version": dep,
                            "type": "runtime",
                            "spec": dep
                        })
                
                if "project" in pyproject_data and "optional-dependencies" in pyproject_data["project"]:
                    for group, deps in pyproject_data["project"]["optional-dependencies"].items():
                        for dep in deps:
                            dev_dependencies.append({
                                "name": dep.split()[0] if ' ' in dep else dep,
                                "version": dep,
                                "type": f"optional-{group}",
                                "spec": dep
                            })
            except ImportError:
                # Fallback: try to parse as TOML manually or skip
                pass
            except Exception:
                pass
        
        # Try Pipfile
        pipfile = self.repo_path / "Pipfile"
        if pipfile.exists():
            package_manager = "pipenv"
            lockfile_present = (self.repo_path / "Pipfile.lock").exists()
            try:
                # Try Python 3.11+ built-in tomllib first
                try:
                    import tomllib
                    with open(pipfile, 'rb') as f:
                        pipfile_data = tomllib.load(f)
                except ImportError:
                    # Fallback to tomli for older Python versions
                    import tomli
                    with open(pipfile, 'rb') as f:
                        pipfile_data = tomli.load(f)
                    
                if "packages" in pipfile_data:
                    for name, spec in pipfile_data["packages"].items():
                        dependencies.append({
                            "name": name,
                            "version": spec if isinstance(spec, str) else str(spec),
                            "type": "runtime",
                            "spec": str(spec)
                        })
                
                if "dev-packages" in pipfile_data:
                    for name, spec in pipfile_data["dev-packages"].items():
                        dev_dependencies.append({
                            "name": name,
                            "version": spec if isinstance(spec, str) else str(spec),
                            "type": "dev",
                            "spec": str(spec)
                        })
            except ImportError:
                pass
            except Exception:
                pass
        
        # Try poetry.lock
        poetry_lock = self.repo_path / "poetry.lock"
        if poetry_lock.exists():
            package_manager = "poetry"
            lockfile_present = True
        
        if dependencies or dev_dependencies or package_manager:
            return {
                "package_manager": package_manager or "pip",
                "lockfile_present": lockfile_present,
                "dependencies": dependencies,
                "dev_dependencies": dev_dependencies,
                "total_dependencies": len(dependencies) + len(dev_dependencies)
            }
        
        return None

