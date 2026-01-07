"""Upload module for evidence packs to external platforms"""

import os
import zipfile
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import requests
from urllib.parse import urljoin, urlparse


class EvidenceUploader:
    """Uploads evidence packs to external compliance platforms"""
    
    def __init__(self, upload_url: str, upload_token: str, 
                 auth_type: str = "bearer", custom_header: Optional[str] = None):
        """
        Initialize uploader
        
        Args:
            upload_url: Base URL for upload endpoint
            upload_token: Authentication token
            auth_type: Type of auth - "bearer", "sas", "custom"
            custom_header: Custom header name if auth_type is "custom" (e.g., "X-API-Key")
        """
        self.upload_url = upload_url.rstrip('/')
        self.upload_token = upload_token
        self.auth_type = auth_type.lower()
        self.custom_header = custom_header or "X-API-Key"
    
    def upload(self, evidence_dir: Path, repo_name: str, commit_sha: str,
               upload_method: str = "zip") -> Dict[str, Any]:
        """
        Upload evidence pack
        
        Args:
            evidence_dir: Directory containing evidence pack
            repo_name: Repository name
            commit_sha: Commit SHA
            upload_method: "zip" (default) or "individual"
        
        Returns:
            Dict with published_url and upload details
        """
        if upload_method == "zip":
            return self._upload_as_zip(evidence_dir, repo_name, commit_sha)
        else:
            return self._upload_individual_files(evidence_dir, repo_name, commit_sha)
    
    def _upload_as_zip(self, evidence_dir: Path, repo_name: str, commit_sha: str) -> Dict[str, Any]:
        """Upload evidence pack as a single ZIP file"""
        # Create ZIP file
        zip_path = evidence_dir.parent / f"evidence-{repo_name}-{commit_sha[:7]}.zip"
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add all files from evidence directory
                for file_path in evidence_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(evidence_dir)
                        zipf.write(file_path, arcname)
            
            zip_size = zip_path.stat().st_size
            
            # Construct upload path
            upload_path = f"/evidence/{repo_name}/{commit_sha}"
            upload_endpoint = urljoin(self.upload_url, upload_path)
            
            # Prepare headers
            headers = self._get_headers()
            
            # Upload ZIP file
            with open(zip_path, 'rb') as f:
                files = {'file': (zip_path.name, f, 'application/zip')}
                data = {
                    'repo_name': repo_name,
                    'commit_sha': commit_sha,
                    'uploaded_at': datetime.now(timezone.utc).isoformat(),
                }
                
                response = requests.post(
                    upload_endpoint,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=300  # 5 minute timeout for large files
                )
                response.raise_for_status()
            
            # Get published URL from response or construct it
            published_url = self._extract_published_url(response, upload_path)
            
            # Clean up ZIP file
            zip_path.unlink()
            
            return {
                "success": True,
                "published_url": published_url,
                "upload_method": "zip",
                "file_size": zip_size,
                "upload_endpoint": upload_endpoint,
            }
            
        except Exception as e:
            # Clean up ZIP file on error
            if zip_path.exists():
                zip_path.unlink()
            raise Exception(f"Failed to upload ZIP: {str(e)}")
    
    def _upload_individual_files(self, evidence_dir: Path, repo_name: str, commit_sha: str) -> Dict[str, Any]:
        """Upload evidence pack files individually"""
        upload_path = f"/evidence/{repo_name}/{commit_sha}"
        base_url = urljoin(self.upload_url, upload_path)
        
        headers = self._get_headers()
        uploaded_files = []
        failed_files = []
        
        # Get all files
        files_to_upload = list(evidence_dir.rglob('*'))
        files_to_upload = [f for f in files_to_upload if f.is_file()]
        
        for file_path in files_to_upload:
            try:
                relative_path = file_path.relative_to(evidence_dir)
                file_url = urljoin(base_url, str(relative_path).replace('\\', '/'))
                
                with open(file_path, 'rb') as f:
                    file_headers = headers.copy()
                    file_headers['Content-Type'] = self._get_content_type(file_path)
                    
                    response = requests.put(
                        file_url,
                        headers=file_headers,
                        data=f,
                        timeout=60
                    )
                    response.raise_for_status()
                
                uploaded_files.append(str(relative_path))
                
            except Exception as e:
                failed_files.append({
                    "file": str(relative_path),
                    "error": str(e)
                })
        
        if failed_files:
            return {
                "success": False,
                "uploaded_files": uploaded_files,
                "failed_files": failed_files,
                "published_url": base_url,
                "upload_method": "individual",
            }
        
        return {
            "success": True,
            "published_url": base_url,
            "uploaded_files": uploaded_files,
            "total_files": len(uploaded_files),
            "upload_method": "individual",
        }
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers based on auth type"""
        headers = {
            'User-Agent': 'repo-analyzer/1.0',
        }
        
        if self.auth_type == "bearer":
            headers['Authorization'] = f'Bearer {self.upload_token}'
        elif self.auth_type == "sas":
            # SAS tokens are usually in the URL, but can also be in header
            headers['Authorization'] = f'SharedAccessSignature {self.upload_token}'
        elif self.auth_type == "custom":
            headers[self.custom_header] = self.upload_token
        else:
            # Default to Bearer
            headers['Authorization'] = f'Bearer {self.upload_token}'
        
        return headers
    
    def _get_content_type(self, file_path: Path) -> str:
        """Get content type for file"""
        suffix = file_path.suffix.lower()
        content_types = {
            '.json': 'application/json',
            '.md': 'text/markdown',
            '.mmd': 'text/plain',
            '.puml': 'text/plain',
            '.png': 'image/png',
            '.txt': 'text/plain',
            '.xml': 'application/xml',
            '.yaml': 'application/x-yaml',
            '.yml': 'application/x-yaml',
        }
        return content_types.get(suffix, 'application/octet-stream')
    
    def _extract_published_url(self, response: requests.Response, default_path: str) -> str:
        """Extract published URL from response or construct default"""
        try:
            # Try to get URL from response JSON
            if response.headers.get('Content-Type', '').startswith('application/json'):
                data = response.json()
                if 'url' in data:
                    return data['url']
                if 'published_url' in data:
                    return data['published_url']
                if 'location' in data:
                    return data['location']
            
            # Try Location header
            if 'Location' in response.headers:
                return response.headers['Location']
            
            # Construct default URL
            return urljoin(self.upload_url, default_path)
            
        except Exception:
            # Fallback to constructed URL
            return urljoin(self.upload_url, default_path)
    
    def upload_manifest(self, evidence_dir: Path, repo_name: str, commit_sha: str) -> Optional[str]:
        """Upload a manifest file describing the evidence pack structure"""
        manifest = {
            "repo_name": repo_name,
            "commit_sha": commit_sha,
            "uploaded_at": datetime.utcnow().isoformat() + 'Z',
            "files": []
        }
        
        # List all files
        for file_path in evidence_dir.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(evidence_dir)
                file_stat = file_path.stat()
                manifest["files"].append({
                    "path": str(relative_path).replace('\\', '/'),
                    "size": file_stat.st_size,
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat() + 'Z',
                })
        
        # Write manifest
        manifest_path = evidence_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        
        return str(manifest_path)

