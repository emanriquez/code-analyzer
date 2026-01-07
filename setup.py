"""Setup script for repo-analyzer package (fallback for older pip versions)"""

from setuptools import setup, find_packages

# Dependencies - keep in sync with pyproject.toml
dependencies = [
    "click>=8.0.0",
    "pyyaml>=6.0",
    "gitpython>=3.1.0",
    "requests>=2.28.0",
    "openai>=1.0.0",
    "google-generativeai>=0.3.0",
    "tomli>=2.0.0; python_version < '3.11'",
]

setup(
    name="repo-analyzer",
    version="1.0.2",
    description="Repository analyzer for generating evidence packs",
    packages=find_packages(),
    install_requires=dependencies,
    entry_points={
        "console_scripts": [
            "repo-analyzer=repo_analyzer.cli:main",
        ],
    },
    python_requires=">=3.8",
)

