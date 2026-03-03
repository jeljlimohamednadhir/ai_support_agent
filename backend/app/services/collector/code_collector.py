"""
Code Collector
Collects and processes code from Git repositories
"""
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import uuid
import shutil

from app.services.knowledge.manager import get_vector_service, get_graph_service

logger = logging.getLogger(__name__)


class CodeCollector:
    """Collects code from Git repositories"""
    
    SUPPORTED_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.sql': 'sql',
    }
    
    IGNORE_DIRS = {
        'node_modules', '__pycache__', '.git', '.venv', 'venv',
        'dist', 'build', 'target', '.idea', '.vscode', 'bin', 'obj'
    }
    
    def __init__(self, repo_url: str = None, branch: str = "main"):
        self.repo_url = repo_url
        self.branch = branch
        self.temp_dir = None
        
        # Services de connaissance (singleton)
        self.vector_service = get_vector_service()
        self.graph_service = get_graph_service()
        
        logger.info("[OK] CodeCollector initialise avec Vector + Graph services (singleton)")
    
    async def collect_from_repository(self, repo_url: str = None, branch: str = None) -> Dict:
        """
        Clone and analyze a Git repository
        
        Args:
            repo_url: Git repository URL
            branch: Branch to analyze
            
        Returns:
            Collection results with artifacts
        """
        repo_url = repo_url or self.repo_url
        branch = branch or self.branch
        job_id = str(uuid.uuid4())
        
        if not repo_url:
            return {
                "job_id": job_id,
                "status": "error",
                "error": "repo_url est requis"
            }
        
        try:
            logger.info(f"Debut collection: {repo_url} (branche: {branch})")
            
            # Import Git
            try:
                import git
            except ImportError:
                logger.error("GitPython non installe")
                return {
                    "job_id": job_id,
                    "status": "error",
                    "error": "GitPython non installe. Executez: pip install gitpython"
                }
            
            # Create temp directory
            self.temp_dir = tempfile.mkdtemp(prefix="git_analysis_")
            target_path = Path(self.temp_dir)
            logger.info(f"Clone dans: {target_path}")
            
            # Clone repository
            await self.clone_repository(target_path, repo_url, branch)
            
            # Analyze code files
            artifacts = await self.parse_code_files(target_path)
            
            # Get statistics
            stats = self.get_statistics(artifacts)
            
            logger.info(f"[OK] {len(artifacts)} fichiers analyses")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "repository": repo_url,
                "branch": branch,
                "artifacts_count": len(artifacts),
                "artifacts": artifacts,
                "statistics": stats,
                "collected_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur collection: {e}")
            return {
                "job_id": job_id,
                "status": "error",
                "error": str(e)
            }
        finally:
            # Cleanup
            if self.temp_dir and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                    logger.info("Dossier temporaire nettoye")
                except Exception as e:
                    logger.warning(f"Impossible de nettoyer {self.temp_dir}: {e}")
    
    async def clone_repository(self, target_dir: Path, repo_url: str = None, branch: str = None):
        """Clone Git repository or copy local repository"""
        import git
        
        repo_url = repo_url or self.repo_url
        branch = branch or self.branch
        
        try:
            # Détecter si c'est un chemin local Windows
            if repo_url and (os.path.isdir(repo_url) or (len(repo_url) > 2 and repo_url[1] == ':')):
                logger.info(f"Copie du repository local: {repo_url}")
                # Copier le repo local
                import shutil
                for item in os.listdir(repo_url):
                    s = os.path.join(repo_url, item)
                    d = os.path.join(target_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                logger.info(f"[OK] Repository local copie")
            else:
                # Cloner depuis URL Git
                repo = git.Repo.clone_from(
                    repo_url,
                    target_dir,
                    branch=branch,
                    depth=1  # Shallow clone for performance
                )
                logger.info(f"[OK] Repository clone: {branch}")
        except Exception as e:
            logger.error(f"Erreur clone: {e}")
            raise
    
    async def parse_code_files(self, repo_path: Path) -> List[Dict]:
        """
        Parse code files and extract:
        - Functions/Classes
        - Imports/Dependencies
        - Comments/Documentation
        - Business logic
        """
        artifacts = []
        
        for file_path in repo_path.rglob('*'):
            # Skip directories
            if file_path.is_dir():
                continue
            
            # Skip ignored directories
            if any(ignored in file_path.parts for ignored in self.IGNORE_DIRS):
                continue
            
            # Check extension
            extension = file_path.suffix.lower()
            if extension not in self.SUPPORTED_EXTENSIONS:
                continue
            
            try:
                # Read content
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Get relative path
                relative_path = file_path.relative_to(repo_path)
                
                artifact = {
                    "name": file_path.name,
                    "path": str(relative_path),
                    "type": "code",
                    "language": self.SUPPORTED_EXTENSIONS[extension],
                    "content": content,
                    "size": len(content),
                    "lines": content.count('\n') + 1,
                    "extension": extension
                }
                
                artifacts.append(artifact)
                
                # === INDEXATION AUTOMATIQUE ===
                file_id = str(uuid.uuid4())
                
                # 1. Ajouter au graphe de connaissances
                await self.graph_service.add_code_node(
                    node_id=file_id,
                    node_type='file',
                    name=file_path.name,
                    content=content[:500],  # Preview
                    metadata={
                        'path': str(relative_path),
                        'language': self.SUPPORTED_EXTENSIONS[extension],
                        'lines': artifact['lines'],
                        'size': artifact['size']
                    }
                )
                
                # 2. Ajouter au store vectoriel (embeddings)
                await self.vector_service.add_code_snippet(
                    code=content,
                    metadata={
                        'file_name': file_path.name,
                        'file_path': str(relative_path),
                        'language': self.SUPPORTED_EXTENSIONS[extension],
                        'lines': artifact['lines']
                    },
                    snippet_id=file_id
                )
                
            except Exception as e:
                logger.warning(f"Impossible de lire {file_path}: {e}")
                continue
        
        return artifacts
    
    async def extract_endpoints(self, repo_path: Path):
        """Extract API endpoints from code"""
        # TODO: Implement endpoint extraction for FastAPI, Flask, etc.
        pass
    
    async def build_dependency_graph(self):
        """Build code dependency graph"""
        # TODO: Implement dependency graph
        pass
    
    def get_statistics(self, artifacts: List[Dict]) -> Dict:
        """Calculate statistics on artifacts"""
        stats = {
            "total_files": len(artifacts),
            "total_lines": sum(a["lines"] for a in artifacts),
            "total_size": sum(a["size"] for a in artifacts),
            "languages": {},
        }
        
        for artifact in artifacts:
            lang = artifact["language"]
            if lang not in stats["languages"]:
                stats["languages"][lang] = {
                    "count": 0,
                    "lines": 0,
                    "size": 0
                }
            
            stats["languages"][lang]["count"] += 1
            stats["languages"][lang]["lines"] += artifact["lines"]
            stats["languages"][lang]["size"] += artifact["size"]
        
        return stats

