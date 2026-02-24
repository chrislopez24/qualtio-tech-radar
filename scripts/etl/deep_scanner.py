from pathlib import Path
from typing import List, Optional
import subprocess
import re


INFRA_TECH_PATTERNS = {
    "argocd": r"argocd",
    "terraform": r"terraform",
    "kubernetes": r"kubernetes|k8s",
    "ansible": r"ansible",
    "vault": r"vault",
    "docker": r"docker",
    "puppet": r"puppet",
    "helm": r"helm",
    "istio": r"istio",
    "prometheus": r"prometheus",
    "grafana": r"grafana",
}


class DeepScanner:
    def __init__(
        self,
        allowed_repos: Optional[List[str]] = None,
        use_ai_analysis: bool = False,
    ):
        self.allowed_repos = allowed_repos or []
        self.use_ai_analysis = use_ai_analysis

    def is_repo_allowed(self, repo_name: str) -> bool:
        if not self.allowed_repos:
            return True
        return repo_name in self.allowed_repos

    def scan_tree(self, tree_file: str) -> List[str]:
        path = Path(tree_file)
        if not path.exists():
            return []

        content = path.read_text()
        return self._extract_technologies(content)

    def _extract_technologies(self, content: str) -> List[str]:
        technologies = []
        content_lower = content.lower()

        for tech, pattern in INFRA_TECH_PATTERNS.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                technologies.append(tech)

        return technologies

    def shallow_clone(self, repo_url: str, dest_dir: str) -> bool:
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", repo_url, dest_dir],
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def extract_tree(self, repo_dir: str, output_file: str) -> bool:
        try:
            result = subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", "HEAD"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            Path(output_file).write_text(result.stdout)
            return True
        except subprocess.CalledProcessError:
            return False