"""Code metrics collector module"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import json


class MetricsCollector:
    """Collects code metrics (lines of code, files, languages)"""
    
    # Common code file extensions
    CODE_EXTENSIONS = {
        # JavaScript/TypeScript
        '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
        # Python
        '.py', '.pyw', '.pyx',
        # Java
        '.java',
        # C/C++
        '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp',
        # Go
        '.go',
        # Rust
        '.rs',
        # Ruby
        '.rb',
        # PHP
        '.php',
        # Swift
        '.swift',
        # Kotlin
        '.kt', '.kts',
        # Scala
        '.scala',
        # Shell
        '.sh', '.bash', '.zsh',
        # HTML/CSS
        '.html', '.htm', '.css', '.scss', '.sass', '.less',
        # Markdown
        '.md', '.markdown',
        # JSON/YAML
        '.json', '.yaml', '.yml',
        # SQL
        '.sql',
        # XML
        '.xml',
        # Config
        '.toml', '.ini', '.cfg', '.conf',
    }
    
    # Directories to ignore
    IGNORE_DIRS = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
        'dist', 'build', '.next', '.nuxt', 'coverage', '.nyc_output',
        'target', 'bin', 'obj', '.idea', '.vscode', '.vs',
        'vendor', 'bower_components', '.pytest_cache', '.mypy_cache',
        '.tox', '.eggs', '*.egg-info', '.sass-cache', '.cache',
    }
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
    
    def collect(self) -> Dict[str, Any]:
        """Collect all metrics"""
        # Try cloc first if available
        cloc_result = self._try_cloc()
        if cloc_result:
            return cloc_result
        
        # Fallback to manual counting
        return self._manual_count()
    
    def _try_cloc(self) -> Optional[Dict[str, Any]]:
        """Try to use cloc tool if available"""
        try:
            # Try to run cloc
            result = subprocess.run(
                ['cloc', '--json', '--quiet', str(self.repo_path)],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(self.repo_path)
            )
            
            if result.returncode == 0 and result.stdout:
                cloc_data = json.loads(result.stdout)
                
                # Extract summary
                summary = cloc_data.get('SUM', {})
                total_lines = summary.get('code', 0)
                total_files = summary.get('nFiles', 0)
                
                # Extract languages breakdown
                languages = {}
                for lang, data in cloc_data.items():
                    if lang not in ['header', 'SUM'] and isinstance(data, dict):
                        languages[lang] = {
                            "files": data.get('nFiles', 0),
                            "lines": data.get('code', 0),
                            "blank": data.get('blank', 0),
                            "comment": data.get('comment', 0),
                        }
                
                return {
                    "lines_of_code": total_lines,
                    "files": total_files,
                    "languages": languages,
                    "blank_lines": summary.get('blank', 0),
                    "comment_lines": summary.get('comment', 0),
                    "method": "cloc"
                }
        except FileNotFoundError:
            # cloc not installed
            pass
        except subprocess.TimeoutExpired:
            # cloc took too long
            pass
        except (json.JSONDecodeError, ValueError, Exception):
            # Failed to parse or other error
            pass
        
        return None
    
    def _manual_count(self) -> Dict[str, Any]:
        """Manually count lines of code and files"""
        languages = {}
        total_lines = 0
        total_files = 0
        total_blank = 0
        total_comment = 0
        
        for file_path in self._walk_code_files():
            try:
                lang = self._detect_language(file_path)
                if not lang:
                    continue
                
                if lang not in languages:
                    languages[lang] = {
                        "files": 0,
                        "lines": 0,
                        "blank": 0,
                        "comment": 0,
                    }
                
                file_stats = self._count_file_lines(file_path, lang)
                
                languages[lang]["files"] += 1
                languages[lang]["lines"] += file_stats["code"]
                languages[lang]["blank"] += file_stats["blank"]
                languages[lang]["comment"] += file_stats["comment"]
                
                total_files += 1
                total_lines += file_stats["code"]
                total_blank += file_stats["blank"]
                total_comment += file_stats["comment"]
                
            except Exception:
                # Skip files that can't be read
                continue
        
        return {
            "lines_of_code": total_lines,
            "files": total_files,
            "languages": languages,
            "blank_lines": total_blank,
            "comment_lines": total_comment,
            "method": "manual"
        }
    
    def _walk_code_files(self):
        """Walk through repository and yield code files"""
        for root, dirs, files in os.walk(self.repo_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith('.')]
            
            for file in files:
                file_path = Path(root) / file
                
                # Skip if in ignored directory
                if any(ignore in str(file_path) for ignore in self.IGNORE_DIRS):
                    continue
                
                # Check if it's a code file
                if file_path.suffix.lower() in self.CODE_EXTENSIONS:
                    yield file_path
    
    def _detect_language(self, file_path: Path) -> Optional[str]:
        """Detect programming language from file extension"""
        ext = file_path.suffix.lower()
        
        lang_map = {
            '.js': 'JavaScript',
            '.jsx': 'JavaScript',
            '.mjs': 'JavaScript',
            '.cjs': 'JavaScript',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript',
            '.py': 'Python',
            '.pyw': 'Python',
            '.java': 'Java',
            '.c': 'C',
            '.cpp': 'C++',
            '.cc': 'C++',
            '.cxx': 'C++',
            '.h': 'C/C++ Header',
            '.hpp': 'C++ Header',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.kts': 'Kotlin',
            '.scala': 'Scala',
            '.sh': 'Shell',
            '.bash': 'Shell',
            '.zsh': 'Shell',
            '.html': 'HTML',
            '.htm': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.sass': 'Sass',
            '.less': 'Less',
            '.md': 'Markdown',
            '.markdown': 'Markdown',
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.sql': 'SQL',
            '.xml': 'XML',
            '.toml': 'TOML',
            '.ini': 'INI',
            '.cfg': 'Config',
            '.conf': 'Config',
        }
        
        return lang_map.get(ext)
    
    def _count_file_lines(self, file_path: Path, lang: str) -> Dict[str, int]:
        """Count lines in a file"""
        code_lines = 0
        blank_lines = 0
        comment_lines = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    stripped = line.strip()
                    
                    if not stripped:
                        blank_lines += 1
                    elif self._is_comment(stripped, lang):
                        comment_lines += 1
                    else:
                        code_lines += 1
        except Exception:
            # If file can't be read, return zeros
            pass
        
        return {
            "code": code_lines,
            "blank": blank_lines,
            "comment": comment_lines,
        }
    
    def _is_comment(self, line: str, lang: str) -> bool:
        """Check if a line is a comment"""
        # Single line comments
        comment_patterns = {
            'JavaScript': ['//', '/*', '*/', '*'],
            'TypeScript': ['//', '/*', '*/', '*'],
            'Python': ['#'],
            'Java': ['//', '/*', '*/', '*'],
            'C': ['//', '/*', '*/', '*'],
            'C++': ['//', '/*', '*/', '*'],
            'Go': ['//', '/*', '*/'],
            'Rust': ['//', '/*', '*/'],
            'Ruby': ['#'],
            'PHP': ['//', '#', '/*', '*/'],
            'Swift': ['//', '/*', '*/'],
            'Kotlin': ['//', '/*', '*/'],
            'Scala': ['//', '/*', '*/'],
            'Shell': ['#'],
            'HTML': ['<!--', '-->'],
            'CSS': ['/*', '*/'],
            'SCSS': ['//', '/*', '*/'],
            'Sass': ['//', '/*', '*/'],
            'SQL': ['--', '/*', '*/'],
        }
        
        patterns = comment_patterns.get(lang, [])
        for pattern in patterns:
            if line.startswith(pattern):
                return True
        
        return False

