"""Repository facts collector"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import git


class RepoFactsCollector:
    """Collects repository metadata and facts"""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
    
    def collect(self, repo_name: Optional[str] = None, 
                commit_sha: Optional[str] = None,
                build_id: Optional[str] = None) -> Dict[str, Any]:
        """Collect repository facts"""
        facts = {
            "name": repo_name or self._get_repo_name(),
            "path": str(self.repo_path),
            "commit_sha": commit_sha or self._get_commit_sha(),
            "branch": self._get_branch(),
            "url": self._get_repo_url(),
            "build_id": build_id or os.environ.get("BUILD_BUILDID"),
            "has_git": self._has_git(),
        }
        
        return facts
    
    def _get_repo_name(self) -> str:
        """Extract repository name from path or git"""
        # Try from git remote first
        try:
            repo = git.Repo(self.repo_path)
            if repo.remotes:
                remote_url = repo.remotes.origin.url
                # Extract repo name from URL
                if remote_url.endswith('.git'):
                    remote_url = remote_url[:-4]
                name = remote_url.split('/')[-1]
                return name
        except Exception:
            pass
        
        # Fallback to directory name
        return self.repo_path.name
    
    def _get_commit_sha(self) -> str:
        """Get current commit SHA"""
        try:
            repo = git.Repo(self.repo_path)
            return repo.head.commit.hexsha
        except Exception:
            return "unknown"
    
    def _get_branch(self) -> str:
        """Get current branch"""
        try:
            repo = git.Repo(self.repo_path)
            return repo.active_branch.name
        except Exception:
            return "unknown"
    
    def _get_repo_url(self) -> str:
        """Get repository URL from git remote"""
        try:
            repo = git.Repo(self.repo_path)
            if repo.remotes:
                return repo.remotes.origin.url
        except Exception:
            pass
        return ""
    
    def _has_git(self) -> bool:
        """Check if repository has git"""
        return (self.repo_path / ".git").exists()

