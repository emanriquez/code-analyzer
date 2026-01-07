"""Scoring system module for calculating VC-Ready Engineering Score"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta


class ScoringSystem:
    """Calculates product quality and engineering scores based on metrics"""
    
    def __init__(self, evidence_pack_path: str, metrica_config_path: Optional[str] = None, 
                 stack_info: Optional[Dict[str, Any]] = None, repo_facts: Optional[Dict[str, Any]] = None,
                 metrics: Optional[Dict[str, Any]] = None):
        self.evidence_pack_path = Path(evidence_pack_path)
        self.stack_info = stack_info or {}
        self.repo_facts = repo_facts or {}
        self.metrics = metrics or {}
        
        # Load metrica config
        # Try to find metrica.json in common locations
        if metrica_config_path:
            config_path = Path(metrica_config_path)
        else:
            # Look for metrica.json in repo root or current directory
            possible_paths = [
                Path("metrica.json"),
                Path("../metrica.json"),
                self.evidence_pack_path.parent / "metrica.json",
                Path(__file__).parent.parent / "metrica.json",
            ]
            config_path = None
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    # Handle case where config is wrapped in a key
                    if "scoring_model" in config_data:
                        self.metrica_config = config_data
                    elif "scoring_model" in config_data.get("scoring_model", {}):
                        # Already wrapped
                        self.metrica_config = config_data
                    else:
                        self.metrica_config = {"scoring_model": config_data}
            except Exception:
                self.metrica_config = self._get_default_config()
        else:
            # Use default config
            self.metrica_config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default metrica configuration"""
        # This would ideally load from metrica.json, but we'll use inline for now
        # The actual config should be loaded from metrica.json file
        return {
            "scoring_model": {
                "name": "VC-Ready Engineering Score",
                "version": "1.0.0",
                "scale": {"min": 0, "max": 100},
                "final_score_weights": {
                    "velocity": 0.2,
                    "stability": 0.15,
                    "scalability": 0.15,
                    "security": 0.15,
                    "maintainability": 0.15,
                    "bus_factor": 0.1,
                    "governance": 0.1
                },
                "dimensions": []
            }
        }
    
    def calculate_scores(self, repo_name: str, commit_sha: str) -> Dict[str, Any]:
        """Calculate all dimension scores and final score"""
        scores = {}
        
        dimensions_config = self.metrica_config.get("scoring_model", {}).get("dimensions", [])
        weights = self.metrica_config.get("scoring_model", {}).get("final_score_weights", {})
        
        # Calculate score for each dimension
        for dimension in dimensions_config:
            dimension_key = dimension.get("key")
            dimension_score = self._calculate_dimension_score(dimension)
            scores[dimension_key] = dimension_score
        
        # Calculate weighted final score
        final_score = 0.0
        for dimension_key, dimension_score in scores.items():
            weight = weights.get(dimension_key, 0)
            final_score += dimension_score * weight
        
        # Calculate product quality rating (1-10 scale)
        product_quality = self._calculate_product_quality_rating(scores)
        
        # Determine grade
        grade = self._score_to_grade(final_score)
        
        # Generate notes
        notes = self._generate_notes(scores, final_score)
        
        result = {
            "repo": repo_name,
            "commit": commit_sha,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scores": scores,
            "final_score": round(final_score, 2),
            "product_quality": {
                "rating": product_quality,
                "scale": {"min": 1, "max": 10}
            },
            "grade": grade,
            "notes": notes
        }
        
        return result
    
    def _calculate_dimension_score(self, dimension: Dict[str, Any]) -> float:
        """Calculate score for a single dimension"""
        metrics = dimension.get("metrics", [])
        if not metrics:
            return 0.0
        
        dimension_score = 0.0
        total_weight = sum(m.get("metric_weight", 0) for m in metrics)
        
        if total_weight == 0:
            return 0.0
        
        # Track if we have any valid values
        has_valid_values = False
        
        for metric in metrics:
            metric_key = metric.get("key")
            metric_weight = metric.get("metric_weight", 0)
            normalization = metric.get("normalization", {})
            
            # Get value from source
            value = self._get_metric_value(metric.get("source", {}))
            
            # If value is None, try to use default or estimate
            if value is None:
                # Try to estimate from available data or use default
                value = self._estimate_metric_value(metric_key, metric, dimension)
            
            # Normalize value to score
            normalized_score = self._normalize_value(value, normalization)
            
            if value is not None:
                has_valid_values = True
            
            # Weight the score (only if we have a value, otherwise use 0)
            if value is not None:
                dimension_score += normalized_score * (metric_weight / total_weight)
        
        # If no valid values, return 0 (or could return a default like 50)
        if not has_valid_values:
            return 0.0
        
        return min(100.0, max(0.0, dimension_score))
    
    def _estimate_metric_value(self, metric_key: str, metric: Dict[str, Any], dimension: Dict[str, Any]) -> Any:
        """Estimate metric value from available data when direct source is not available"""
        # Try to estimate based on available evidence pack data
        dimension_key = dimension.get("key")
        
        # Velocity dimension estimations
        if dimension_key == "velocity":
            if metric_key == "deploys_per_month":
                # Estimate based on commit frequency and tech stack
                commits_file = self.evidence_pack_path / "change" / "commits.json"
                if commits_file.exists():
                    try:
                        with open(commits_file, 'r') as f:
                            data = json.load(f)
                            recent_commits = data.get("recent_commits", [])
                            if recent_commits:
                                # Count commits in last 30 days
                                from datetime import datetime, timedelta, timezone
                                now = datetime.now(timezone.utc)
                                days_30_ago = now - timedelta(days=30)
                                
                                commits_30d = sum(1 for c in recent_commits 
                                                 if self._parse_commit_date(c.get("date", "")) >= days_30_ago)
                                
                                # Modern frameworks like NestJS typically have faster deployment
                                frameworks = self.stack_info.get("frameworks", [])
                                has_modern_stack = any(f in ["NestJS", "Next.js", "FastAPI"] for f in frameworks)
                                
                                # Estimate deploys: if many commits and modern stack, likely frequent deploys
                                if commits_30d >= 20 and has_modern_stack:
                                    return 10  # Good velocity
                                elif commits_30d >= 10:
                                    return 4   # Moderate velocity
                                elif commits_30d >= 5:
                                    return 1   # Low velocity
                    except:
                        pass
                
                # Default: modern stack = moderate velocity assumption
                frameworks = self.stack_info.get("frameworks", [])
                if any(f in ["NestJS", "Next.js", "FastAPI"] for f in frameworks):
                    return 4  # Assume moderate deployment frequency
                return 0
                
            elif metric_key == "lead_time_pr_to_prod_hours":
                # Estimate based on tech stack maturity
                frameworks = self.stack_info.get("frameworks", [])
                has_modern_stack = any(f in ["NestJS", "Next.js", "FastAPI"] for f in frameworks)
                has_typescript = self.stack_info.get("has_typescript", False)
                
                if has_modern_stack and has_typescript:
                    return 24  # Modern stack = faster CI/CD typically
                elif has_modern_stack:
                    return 48
                else:
                    return 96  # Older stack = slower typically
            
            elif metric_key == "features_shipped_per_month":
                # Estimate based on commits and activity
                commits_file = self.evidence_pack_path / "change" / "commits.json"
                if commits_file.exists():
                    try:
                        with open(commits_file, 'r') as f:
                            data = json.load(f)
                            recent_commits = data.get("recent_commits", [])
                            if recent_commits:
                                # Look for feature commits (feat:, feature, new, add)
                                feature_keywords = ["feat", "feature", "new", "add", "implement"]
                                feature_commits = sum(1 for c in recent_commits[:20]
                                                     if any(kw in c.get("message", "").lower() for kw in feature_keywords))
                                return min(feature_commits, 12)  # Cap at 12
                    except:
                        pass
                return 2  # Default moderate
        
        # Stability dimension estimations
        elif dimension_key == "stability":
            if metric_key == "change_failure_rate_pct":
                # Estimate based on architecture quality
                # Modern frameworks with good structure = lower failure rate
                frameworks = self.stack_info.get("frameworks", [])
                has_typescript = self.stack_info.get("has_typescript", False)
                
                if "NestJS" in frameworks and has_typescript:
                    return 5  # Good architecture = low failure rate
                elif has_typescript:
                    return 10
                else:
                    return 15  # Default moderate
                    
            elif metric_key == "mttr_minutes":
                # Modern stack = faster recovery
                frameworks = self.stack_info.get("frameworks", [])
                if "NestJS" in frameworks:
                    return 60  # Good recovery time
                return 120  # Default moderate
                
            elif metric_key == "prod_incidents_last_30d":
                # Default to low if no data (assume stable)
                return 0
        
        # Scalability dimension estimations
        elif dimension_key == "scalability":
            if metric_key == "stateless_services_pct":
                # Detect if using microservices/modular architecture
                frameworks = self.stack_info.get("frameworks", [])
                
                # NestJS with modules = good stateless architecture
                if "NestJS" in frameworks:
                    # Check if has multiple modules/files (indicates modularity)
                    files_count = self.metrics.get("files", 0)
                    if files_count > 20:
                        return 90  # NestJS with many files = modular
                    return 75
                
                # Express or similar = could be stateless
                if "Express" in frameworks:
                    return 70
                
                return 60  # Default moderate
                
            elif metric_key == "async_processing_present":
                # Check dependencies for queue/worker libraries
                deps_file = self.evidence_pack_path / "dependencies.json"
                if deps_file.exists():
                    try:
                        with open(deps_file, 'r') as f:
                            deps = json.load(f)
                            dep_names = [d.get("name", "").lower() for d in deps.get("dependencies", [])]
                            # Check for async/queue libraries
                            async_keywords = ["bull", "bullmq", "rabbitmq", "redis", "queue", "celery", "kafka"]
                            if any(kw in " ".join(dep_names) for kw in async_keywords):
                                return True
                    except:
                        pass
                
                # Check repo name or structure hints
                repo_name = self.repo_facts.get("name", "").lower()
                if any(kw in repo_name for kw in ["scheduler", "worker", "queue", "job"]):
                    return True
                
                return False
                
            elif metric_key == "autoscaling_configured":
                # Check for k8s/docker configs (would need to scan files, but default False for now)
                return False
        
        # Security dimension estimations
        elif dimension_key == "security":
            if metric_key == "critical_cves_open":
                # Try to get from security summary
                security_file = self.evidence_pack_path / "security" / "deps-sca.json"
                if security_file.exists():
                    try:
                        with open(security_file, 'r') as f:
                            data = json.load(f)
                            return data.get("summary", {}).get("critical", 0)
                    except:
                        pass
                return 0  # No critical CVEs = good
            elif metric_key == "secrets_detected":
                # Check if there's a secrets file
                secrets_file = self.evidence_pack_path / "security" / "secrets.json"
                if secrets_file.exists():
                    try:
                        with open(secrets_file, 'r') as f:
                            data = json.load(f)
                            return data.get("secrets_found", 0)
                    except:
                        pass
                return 0  # No secrets found = good
        
        # Maintainability dimension estimations
        elif dimension_key == "maintainability":
            if metric_key == "coverage_core_pct":
                # Try to get from coverage summary
                coverage_file = self.evidence_pack_path / "quality" / "coverage-summary.json"
                if coverage_file.exists():
                    try:
                        with open(coverage_file, 'r') as f:
                            data = json.load(f)
                            # Check if data has coverage info
                            if data and "lines" in data:
                                return data.get("lines", 0)
                    except:
                        pass
                # Default: no coverage = 0%
                return 0
        
        # Bus factor dimension estimations
        elif dimension_key == "bus_factor":
            if metric_key in ["top1_author_share_pct", "active_maintainers_count"]:
                # Calculate from commits if available
                commits_file = self.evidence_pack_path / "change" / "commits.json"
                if commits_file.exists():
                    try:
                        with open(commits_file, 'r') as f:
                            data = json.load(f)
                            if metric_key == "top1_author_share_pct":
                                return self._calculate_top1_share(data)
                            elif metric_key == "active_maintainers_count":
                                return self._calculate_active_maintainers(data)
                    except:
                        pass
        
        # Governance dimension estimations
        elif dimension_key == "governance":
            if metric_key == "ci_cd_present":
                # Check if has CI/CD based on repo structure or build info
                build_file = self.evidence_pack_path / "build" / "build.json"
                if build_file.exists():
                    try:
                        with open(build_file, 'r') as f:
                            build_data = json.load(f)
                            if build_data.get("ci_cd"):
                                return True
                    except:
                        pass
                
                # Check if has common CI/CD files (would need to check repo, but assume True if build.json exists)
                return build_file.exists()
                
            elif metric_key == "onboarding_docs_present":
                # Check if README exists in docs
                readme_file = self.evidence_pack_path / "docs" / "README.enriched.md"
                return readme_file.exists()
            elif metric_key == "runbooks_present":
                # Check if runbook exists
                runbook_file = self.evidence_pack_path / "docs" / "runbook.md"
                return runbook_file.exists()
            elif metric_key == "adrs_present":
                # Check for ADR directory
                repo_root = self.evidence_pack_path.parent
                adr_dirs = ["docs/adr", "adr", "docs/decisions"]
                return any((repo_root / d).exists() for d in adr_dirs)
            elif metric_key == "evidence_per_build_published":
                # Check if build.json exists
                build_file = self.evidence_pack_path / "build" / "build.json"
                return build_file.exists()
        
        # Maintainability dimension estimations
        elif dimension_key == "maintainability":
            if metric_key == "sonar_maintainability_rating":
                # Estimate based on code quality indicators
                frameworks = self.stack_info.get("frameworks", [])
                has_typescript = self.stack_info.get("has_typescript", False)
                
                # Modern stack with TypeScript = good maintainability
                if "NestJS" in frameworks and has_typescript:
                    return "B"  # Good rating
                elif has_typescript:
                    return "C"  # Moderate
                else:
                    return "C"  # Default moderate
                    
            elif metric_key == "duplication_pct":
                # Estimate based on framework quality
                # Modern frameworks encourage DRY principles
                frameworks = self.stack_info.get("frameworks", [])
                if "NestJS" in frameworks:
                    return 3  # Low duplication
                return 8  # Default moderate
                
            elif metric_key == "coverage_core_pct":
                # Try to get from coverage file, or estimate based on test files
                coverage_file = self.evidence_pack_path / "quality" / "coverage-summary.json"
                if coverage_file.exists():
                    try:
                        with open(coverage_file, 'r') as f:
                            data = json.load(f)
                            if data and "lines" in data:
                                return data.get("lines", 0)
                    except:
                        pass
                return 0  # No coverage = 0
        
        return None  # Could not estimate
    
    def _parse_commit_date(self, date_str: str) -> Optional[datetime]:
        """Parse commit date string to datetime"""
        if not date_str:
            return None
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            return date
        except:
            return None
    
    def _get_metric_value(self, source: Dict[str, Any]) -> Any:
        """Get metric value from evidence pack file with field mapping"""
        if not source:
            return None
        
        source_path = source.get("path")
        source_field = source.get("field")
        
        if not source_path or not source_field:
            return None
        
        # Construct full path
        file_path = self.evidence_pack_path / source_path
        
        if not file_path.exists():
            # Try alternative paths or field mappings
            return self._get_metric_value_fallback(source_path, source_field)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Field mapping for common mismatches
            field_mapping = {
                "security/deps-sca.json": {
                    "critical_open": "summary.critical",
                    "high_open": "summary.high",
                    "medium_open": "summary.medium",
                },
                "change/commits.json": {
                    "contributors.top1_share_pct": self._calculate_top1_share,
                    "contributors.active_maintainers_90d": self._calculate_active_maintainers,
                },
                "quality/coverage-summary.json": {
                    "core_modules_coverage_pct": "lines",
                },
            }
            
            # Check if there's a mapping for this file/field
            if source_path in field_mapping and source_field in field_mapping[source_path]:
                mapped = field_mapping[source_path][source_field]
                if callable(mapped):
                    # It's a function to calculate the value
                    return mapped(data)
                else:
                    # It's a different field path
                    source_field = mapped
            
            # Handle nested field paths (e.g., "summary.total" or "contributors.top1_share_pct")
            if "." in source_field:
                parts = source_field.split(".")
                value = data
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        return None
                    if value is None:
                        return None
                return value
            else:
                return data.get(source_field)
        except Exception:
            return None
    
    def _get_metric_value_fallback(self, source_path: str, source_field: str) -> Any:
        """Try to get metric value from alternative sources"""
        # Try alternative field paths
        alternative_paths = {
            "security/deps-sca.json": ["security/deps-sca.json", "security/security.json"],
            "quality/sonar.json": ["quality/sonar.json", "quality/quality.json"],
            "change/commits.json": ["change/commits.json", "change/history.json"],
        }
        
        if source_path in alternative_paths:
            for alt_path in alternative_paths[source_path]:
                alt_file = self.evidence_pack_path / alt_path
                if alt_file.exists():
                    try:
                        with open(alt_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        # Try to extract the value using the same logic
                        if "." in source_field:
                            parts = source_field.split(".")
                            value = data
                            for part in parts:
                                if isinstance(value, dict):
                                    value = value.get(part)
                                else:
                                    break
                                if value is None:
                                    break
                            if value is not None:
                                return value
                        else:
                            value = data.get(source_field)
                            if value is not None:
                                return value
                    except Exception:
                        continue
        
        return None
    
    def _calculate_top1_share(self, commits_data: Dict[str, Any]) -> float:
        """Calculate top 1 author share percentage from commits"""
        if not commits_data or "recent_commits" not in commits_data:
            return 0.0
        
        commits = commits_data.get("recent_commits", [])
        if not commits:
            return 0.0
        
        # Count commits by author
        author_counts = {}
        for commit in commits:
            author = commit.get("author", {})
            author_email = author.get("email", "unknown")
            author_counts[author_email] = author_counts.get(author_email, 0) + 1
        
        if not author_counts:
            return 0.0
        
        # Get top author
        total_commits = len(commits)
        max_commits = max(author_counts.values())
        
        # Calculate percentage
        top1_share = (max_commits / total_commits) * 100.0
        
        return top1_share
    
    def _calculate_active_maintainers(self, commits_data: Dict[str, Any]) -> int:
        """Calculate active maintainers in last 90 days"""
        if not commits_data or "recent_commits" not in commits_data:
            return 0
        
        from datetime import datetime, timedelta, timezone
        
        commits = commits_data.get("recent_commits", [])
        if not commits:
            return 0
        
        # Get date 90 days ago
        now = datetime.now(timezone.utc)
        days_90_ago = now - timedelta(days=90)
        
        # Count unique authors in last 90 days
        active_authors = set()
        for commit in commits:
            commit_date_str = commit.get("date", "")
            if not commit_date_str:
                continue
            
            try:
                # Try to parse date (handle various formats)
                commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
                if commit_date.tzinfo is None:
                    # Assume UTC if no timezone
                    commit_date = commit_date.replace(tzinfo=timezone.utc)
                
                if commit_date >= days_90_ago:
                    author = commit.get("author", {})
                    author_email = author.get("email", "unknown")
                    active_authors.add(author_email)
            except Exception:
                continue
        
        return len(active_authors)
    
    def _normalize_value(self, value: Any, normalization: Dict[str, Any]) -> float:
        """Normalize a metric value to a score (0-100)"""
        if value is None:
            return 0.0
        
        norm_type = normalization.get("type")
        
        if norm_type == "thresholds":
            return self._normalize_thresholds(value, normalization)
        elif norm_type == "boolean":
            return self._normalize_boolean(value, normalization)
        elif norm_type == "mapping":
            return self._normalize_mapping(value, normalization)
        else:
            return 0.0
    
    def _normalize_thresholds(self, value: float, normalization: Dict[str, Any]) -> float:
        """Normalize using threshold-based scoring"""
        thresholds = normalization.get("thresholds", [])
        direction = normalization.get("direction", "higher_is_better")
        interpolate = normalization.get("interpolate_between_points", False)
        
        if not thresholds:
            return 0.0
        
        # Handle boolean values
        if isinstance(value, bool):
            value = 1.0 if value else 0.0
        
        # Convert to float
        try:
            value = float(value)
        except (ValueError, TypeError):
            return 0.0
        
        # Separate thresholds by type (lte vs gte)
        lte_thresholds = [t for t in thresholds if "lte" in t]
        gte_thresholds = [t for t in thresholds if "gte" in t]
        
        # Handle "lte" (lower than or equal) thresholds (for lower_is_better)
        if lte_thresholds and direction == "lower_is_better":
            sorted_thresholds = sorted(lte_thresholds, key=lambda x: x.get("lte", 0))
            for i, threshold in enumerate(sorted_thresholds):
                threshold_value = threshold.get("lte", 0)
                threshold_score = threshold.get("score", 0)
                if value <= threshold_value:
                    if interpolate and i > 0:
                        # Interpolate between previous and current
                        prev_threshold = sorted_thresholds[i-1]
                        prev_value = prev_threshold.get("lte", 0)
                        prev_score = prev_threshold.get("score", 0)
                        if threshold_value != prev_value:
                            ratio = (value - prev_value) / (threshold_value - prev_value)
                            return prev_score + (threshold_score - prev_score) * ratio
                    return threshold_score
            # Value is greater than all thresholds, use last score
            return sorted_thresholds[-1].get("score", 0) if sorted_thresholds else 0.0
        
        # Handle "gte" (greater than or equal) thresholds (for higher_is_better)
        if gte_thresholds and direction == "higher_is_better":
            sorted_thresholds = sorted(gte_thresholds, key=lambda x: x.get("gte", 0), reverse=True)
            for i, threshold in enumerate(sorted_thresholds):
                threshold_value = threshold.get("gte", 0)
                threshold_score = threshold.get("score", 0)
                if value >= threshold_value:
                    if interpolate and i > 0:
                        # Interpolate between current and next (higher)
                        next_threshold = sorted_thresholds[i-1] if i > 0 else None
                        if next_threshold:
                            next_value = next_threshold.get("gte", 0)
                            next_score = next_threshold.get("score", 0)
                            if next_value != threshold_value:
                                ratio = (value - threshold_value) / (next_value - threshold_value)
                                return threshold_score + (next_score - threshold_score) * ratio
                    return threshold_score
            # Value is less than all thresholds, use last score
            return sorted_thresholds[-1].get("score", 0) if sorted_thresholds else 0.0
        
        # Mixed thresholds (both lte and gte)
        # Find the matching threshold
        best_match = None
        for threshold in thresholds:
            if "lte" in threshold and value <= threshold.get("lte", 0):
                if not best_match or threshold.get("lte", 0) < best_match.get("lte", 0):
                    best_match = threshold
            elif "gte" in threshold and value >= threshold.get("gte", 0):
                if not best_match or threshold.get("gte", 0) > best_match.get("gte", 0):
                    best_match = threshold
        
        if best_match:
            return best_match.get("score", 0)
        
        return 0.0
    
    def _normalize_boolean(self, value: bool, normalization: Dict[str, Any]) -> float:
        """Normalize boolean value"""
        if value:
            return normalization.get("true_score", 100)
        else:
            return normalization.get("false_score", 0)
    
    def _normalize_mapping(self, value: Any, normalization: Dict[str, Any]) -> float:
        """Normalize using mapping"""
        mapping = normalization.get("mapping", {})
        return mapping.get(str(value), 0)
    
    def _calculate_product_quality_rating(self, dimension_scores: Dict[str, float]) -> float:
        """Calculate product quality rating (1-10) based on dimension scores"""
        # Product quality considers: maintainability, security, scalability, and code quality
        quality_dims = ["maintainability", "security", "scalability"]
        
        quality_score = 0.0
        count = 0
        
        for dim in quality_dims:
            if dim in dimension_scores:
                quality_score += dimension_scores[dim]
                count += 1
        
        if count == 0:
            return 1.0
        
        avg_score = quality_score / count
        
        # Convert 0-100 score to 1-10 rating
        # Map 0-100 to 1-10 with linear scaling
        rating = 1.0 + (avg_score / 100.0) * 9.0
        
        return round(rating, 1)
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numeric score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "E"
    
    def _generate_notes(self, scores: Dict[str, float], final_score: float) -> List[str]:
        """Generate notes about the scores"""
        notes = []
        
        # Find lowest scoring dimensions
        sorted_dims = sorted(scores.items(), key=lambda x: x[1])
        
        if sorted_dims:
            lowest_dim, lowest_score = sorted_dims[0]
            if lowest_score < 50:
                notes.append(f"Lowest scoring dimension: {lowest_dim} ({lowest_score:.1f}/100). Needs improvement.")
        
        # Overall assessment
        if final_score >= 80:
            notes.append("Strong engineering practices. Ready for VC evaluation.")
        elif final_score >= 60:
            notes.append("Good engineering foundation. Some areas need improvement.")
        else:
            notes.append("Engineering practices need significant improvement before VC evaluation.")
        
        return notes

