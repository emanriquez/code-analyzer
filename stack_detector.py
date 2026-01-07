"""Tech stack detection module"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class TechStack:
    """Detected technology stack information"""
    primary_language: str
    frameworks: List[str]
    package_manager: Optional[str]
    build_tool: Optional[str]
    runtime: Optional[str]
    has_typescript: bool
    is_mobile: bool
    detected_files: List[str]


class StackDetector:
    """Detects technology stack from repository structure"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.detected_files: Set[str] = set()
    
    def detect(self) -> TechStack:
        """Main detection method"""
        # Scan for key files
        self._scan_files()
        
        # Detect primary language
        primary_lang = self._detect_primary_language()
        
        # Detect frameworks
        frameworks = self._detect_frameworks()
        
        # Detect package manager
        package_manager = self._detect_package_manager()
        
        # Detect build tool
        build_tool = self._detect_build_tool()
        
        # Detect runtime
        runtime = self._detect_runtime()
        
        # Check for TypeScript
        has_typescript = self._has_typescript()
        
        # Check if mobile (React Native)
        is_mobile = self._is_mobile()
        
        return TechStack(
            primary_language=primary_lang,
            frameworks=frameworks,
            package_manager=package_manager,
            build_tool=build_tool,
            runtime=runtime,
            has_typescript=has_typescript,
            is_mobile=is_mobile,
            detected_files=sorted(list(self.detected_files))
        )
    
    def _scan_files(self):
        """Scan repository for key files"""
        key_files = [
            # Node.js ecosystem
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "tsconfig.json",
            "jsconfig.json",
            "nest-cli.json",
            "angular.json",
            "next.config.js",
            "next.config.ts",
            "vite.config.js",
            "vite.config.ts",
            "webpack.config.js",
            "craco.config.js",
            
            # React Native
            "app.json",
            "metro.config.js",
            "react-native.config.js",
            "android/",
            "ios/",
            
            # Python
            "requirements.txt",
            "requirements-dev.txt",
            "setup.py",
            "pyproject.toml",
            "Pipfile",
            "poetry.lock",
            "manage.py",  # Django
            "django_settings.py",
            "fastapi_app.py",
            "main.py",
            
            # Other
            ".gitignore",
            "README.md",
        ]
        
        for root, dirs, files in os.walk(self.repo_path):
            # Skip common ignore patterns
            if any(skip in root for skip in ['node_modules', '.git', '__pycache__', '.venv', 'venv']):
                continue
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.repo_path)
                
                if any(key_file in str(rel_path) for key_file in key_files):
                    self.detected_files.add(str(rel_path))
    
    def _detect_primary_language(self) -> str:
        """Detect primary programming language"""
        # Check for Python files
        python_files = list(self.repo_path.rglob("*.py"))
        if python_files and not any("node_modules" in str(p) for p in python_files):
            return "Python"
        
        # Check for JavaScript/TypeScript files
        js_files = list(self.repo_path.rglob("*.js"))
        ts_files = list(self.repo_path.rglob("*.ts"))
        jsx_files = list(self.repo_path.rglob("*.jsx"))
        tsx_files = list(self.repo_path.rglob("*.tsx"))
        
        if js_files or ts_files or jsx_files or tsx_files:
            # Filter out node_modules
            js_files = [f for f in js_files if "node_modules" not in str(f)]
            ts_files = [f for f in ts_files if "node_modules" not in str(f)]
            jsx_files = [f for f in jsx_files if "node_modules" not in str(f)]
            tsx_files = [f for f in tsx_files if "node_modules" not in str(f)]
            
            if js_files or ts_files or jsx_files or tsx_files:
                return "JavaScript"
        
        return "Unknown"
    
    def _detect_frameworks(self) -> List[str]:
        """Detect frameworks and libraries"""
        frameworks = []
        
        # Check package.json for dependencies
        package_json = self.repo_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    pkg_data = json.load(f)
                    deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                    
                    # NestJS
                    if "@nestjs/core" in deps or "@nestjs/common" in deps:
                        frameworks.append("NestJS")
                    
                    # React
                    if "react" in deps:
                        frameworks.append("React")
                    
                    # Next.js
                    if "next" in deps:
                        frameworks.append("Next.js")
                    
                    # Angular
                    if "@angular/core" in deps:
                        frameworks.append("Angular")
                    
                    # Vue
                    if "vue" in deps:
                        frameworks.append("Vue")
                    
                    # React Native
                    if "react-native" in deps:
                        frameworks.append("React Native")
                    
                    # Express
                    if "express" in deps:
                        frameworks.append("Express")
            except Exception:
                pass
        
        # Check for NestJS CLI config
        if (self.repo_path / "nest-cli.json").exists():
            if "NestJS" not in frameworks:
                frameworks.append("NestJS")
        
        # Check for Django
        if (self.repo_path / "manage.py").exists():
            frameworks.append("Django")
        
        # Check for FastAPI
        fastapi_files = list(self.repo_path.rglob("*fastapi*.py"))
        if fastapi_files:
            frameworks.append("FastAPI")
        
        # Check for Flask
        flask_files = list(self.repo_path.rglob("*flask*.py"))
        if flask_files:
            frameworks.append("Flask")
        
        return frameworks
    
    def _detect_package_manager(self) -> Optional[str]:
        """Detect package manager"""
        if (self.repo_path / "pnpm-lock.yaml").exists():
            return "pnpm"
        elif (self.repo_path / "yarn.lock").exists():
            return "yarn"
        elif (self.repo_path / "package-lock.json").exists():
            return "npm"
        elif (self.repo_path / "package.json").exists():
            return "npm"  # Default to npm if package.json exists
        elif (self.repo_path / "requirements.txt").exists() or (self.repo_path / "pyproject.toml").exists():
            return "pip"
        elif (self.repo_path / "Pipfile").exists():
            return "pipenv"
        elif (self.repo_path / "poetry.lock").exists():
            return "poetry"
        
        return None
    
    def _detect_build_tool(self) -> Optional[str]:
        """Detect build tool"""
        # Webpack
        if (self.repo_path / "webpack.config.js").exists() or (self.repo_path / "webpack.config.ts").exists():
            return "webpack"
        
        # Vite
        if (self.repo_path / "vite.config.js").exists() or (self.repo_path / "vite.config.ts").exists():
            return "vite"
        
        # Next.js (has built-in build)
        if (self.repo_path / "next.config.js").exists() or (self.repo_path / "next.config.ts").exists():
            return "next"
        
        # Create React App
        if (self.repo_path / "craco.config.js").exists():
            return "craco"
        
        # Check package.json scripts
        package_json = self.repo_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    pkg_data = json.load(f)
                    scripts = pkg_data.get("scripts", {})
                    if "build" in scripts:
                        # Try to infer from build script
                        build_cmd = scripts.get("build", "")
                        if "webpack" in build_cmd:
                            return "webpack"
                        elif "vite" in build_cmd:
                            return "vite"
            except Exception:
                pass
        
        return None
    
    def _detect_runtime(self) -> Optional[str]:
        """Detect runtime environment"""
        # Node.js
        if (self.repo_path / "package.json").exists():
            return "Node.js"
        
        # Python
        if (self.repo_path / "requirements.txt").exists() or (self.repo_path / "pyproject.toml").exists():
            return "Python"
        
        return None
    
    def _has_typescript(self) -> bool:
        """Check if project uses TypeScript"""
        # Check for tsconfig.json
        if (self.repo_path / "tsconfig.json").exists():
            return True
        
        # Check for .ts/.tsx files
        ts_files = list(self.repo_path.rglob("*.ts"))
        tsx_files = list(self.repo_path.rglob("*.tsx"))
        
        # Filter out node_modules
        ts_files = [f for f in ts_files if "node_modules" not in str(f)]
        tsx_files = [f for f in tsx_files if "node_modules" not in str(f)]
        
        return len(ts_files) > 0 or len(tsx_files) > 0
    
    def _is_mobile(self) -> bool:
        """Check if project is mobile (React Native)"""
        # Check for React Native specific files
        if (self.repo_path / "app.json").exists():
            return True
        
        if (self.repo_path / "android").exists() or (self.repo_path / "ios").exists():
            return True
        
        if (self.repo_path / "metro.config.js").exists():
            return True
        
        # Check package.json for react-native
        package_json = self.repo_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    pkg_data = json.load(f)
                    deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                    if "react-native" in deps:
                        return True
            except Exception:
                pass
        
        return False

