import os
import shutil
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from backend.app.core.config import settings

class VectorDBService:
    def __init__(self):
        self.persist_directory = settings.CHROMA_DB_PATH
        self.embeddings = None
        self._init_embeddings()

    def _init_embeddings(self):
        """
        Initializes local sentence embeddings.
        Supports graceful mock fallback if offline or in Demo Mode.
        """
        if settings.DEMO_MODE:
            self.embeddings = None
            return

        try:
            # Lazy-load HuggingFaceEmbeddings to avoid memory issues on startup
            from langchain_community.embeddings import HuggingFaceEmbeddings
            
            # CPU-friendly free offline embeddings (384-dimensional vectors)
            self.embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDINGS_MODEL,
                model_kwargs={'device': 'cpu'}
            )
        except Exception as e:
            print(f"Failed to initialize HuggingFaceEmbeddings locally: {e}. Falling back to Mock Embeddings.")
            self.embeddings = None

    def _get_db(self, repo_full_name: str) -> Optional[Chroma]:
        """
        Returns a Chroma client instance namespaced for a specific repository.
        """
        if self.embeddings is None:
            return None
            
        safe_name = repo_full_name.replace("/", "_").replace("-", "_")
        repo_persist_dir = os.path.join(self.persist_directory, safe_name)
        
        return Chroma(
            persist_directory=repo_persist_dir,
            embedding_function=self.embeddings
        )

    def _split_code_by_language(self, content: str, file_path: str) -> List[str]:
        """
        Splits code content using LangChain syntax splitters matching file extensions.
        """
        ext = os.path.splitext(file_path)[1].lower()
        lang_mapping = {
            ".py": Language.PYTHON,
            ".js": Language.JS,
            ".ts": Language.TS,
            ".jsx": Language.JS,
            ".tsx": Language.TS,
            ".html": Language.HTML,
            ".css": Language.HTML, # Recursive splitter fits fine
            ".go": Language.GO,
            ".java": Language.JAVA,
            ".cpp": Language.CPP,
            ".c": Language.CPP
        }
        
        selected_lang = lang_mapping.get(ext)
        
        if selected_lang:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=selected_lang,
                chunk_size=1000,
                chunk_overlap=150
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150
            )
            
        return splitter.split_text(content)

    async def index_repository(self, repo_full_name: str, local_path: str) -> bool:
        """
        Walks a local repository clone, chunks source files, indexes them in ChromaDB.
        """
        if settings.DEMO_MODE or self.embeddings is None:
            # Simulate high-fidelity indexing logs
            print(f"DEMO MODE: Simulating ChromaDB indexing for {repo_full_name}")
            return True

        safe_name = repo_full_name.replace("/", "_").replace("-", "_")
        repo_persist_dir = os.path.join(self.persist_directory, safe_name)
        
        # Clear existing index if it exists
        if os.path.exists(repo_persist_dir):
            shutil.rmtree(repo_persist_dir)

        ignored_dirs = {".git", "node_modules", "venv", ".venv", "build", "dist", "__pycache__", ".chroma_db"}
        ignored_extensions = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz", ".db", ".sqlite"}

        texts = []
        metadatas = []

        # Recursively scan repository
        for root, dirs, files in os.walk(local_path):
            # Prune directory tree
            dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ignored_extensions or file.startswith("."):
                    continue
                    
                absolute_path = os.path.join(root, file)
                relative_path = os.path.relpath(absolute_path, local_path)
                
                try:
                    with open(absolute_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        
                    if not content.strip():
                        continue
                        
                    chunks = self._split_code_by_language(content, relative_path)
                    
                    for chunk in chunks:
                        texts.append(chunk)
                        metadatas.append({
                            "file_path": relative_path,
                            "filename": file
                        })
                except Exception as e:
                    print(f"Could not index file {relative_path}: {e}")

        if not texts:
            return False

        # Build and persist Chroma Database
        db = Chroma.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
            persist_directory=repo_persist_dir
        )
        db.persist()
        return True

    async def search_codebase(self, repo_full_name: str, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Executes semantic search against indexed codebase.
        """
        if settings.DEMO_MODE or self.embeddings is None:
            # Return realistic mock semantic search matches
            return [
                {
                    "content": "def process_charge(amount: int, token: str):\n    # Stripe Charge gateway logic helper",
                    "file_path": "services/payment_service.py",
                    "score": 0.85
                },
                {
                    "content": "class User(Base):\n    __tablename__ = 'users'\n    id = Column(Integer, primary_key=True)",
                    "file_path": "models/user.py",
                    "score": 0.72
                }
            ]

        db = self._get_db(repo_full_name)
        if not db:
            return []

        results = db.similarity_search_with_relevance_scores(query, k=k)
        
        formatted_matches = []
        for doc, score in results:
            formatted_matches.append({
                "content": doc.page_content,
                "file_path": doc.metadata.get("file_path", "unknown"),
                "score": round(float(score), 2)
            })
            
        return formatted_matches
