from __future__ import annotations
import os, csv, re, json, yaml
from dataclasses import dataclass
from typing import List
from sentence_transformers import SentenceTransformer
import chromadb

# LangChain + LlamaIndex + ChromaDB integration (mandatory for assignment)
try:
    # LangChain imports
    from langchain_huggingface import HuggingFaceEmbeddings as LangChainEmbeddings
    from langchain_chroma import Chroma as LangChainChroma
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

try:
    # LlamaIndex imports for support integration
    from llama_index.core import VectorStoreIndex, Document as LlamaDocument
    from llama_index.vector_stores.chroma import ChromaVectorStore as LlamaChromaStore
    from llama_index.embeddings.langchain import LangchainEmbedding
    from llama_index.core import Settings
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False

@dataclass
class Hit:
    doc_id: str
    tenant: str
    visibility: str
    page: str
    text: str
    score: float
    pii_masked: bool = False

def load_manifest(base_dir: str) -> list[dict]:
    mpath = os.path.join(base_dir, "data", "manifest.csv")
    with open(mpath, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def read_doc(base_dir: str, rel_path: str) -> str:
    with open(os.path.join(base_dir, rel_path), encoding="utf-8") as f:
        return f.read()

class Retriever:
    def __init__(self, base_dir: str, config_path: str = "config.yaml"):
        self.base_dir = base_dir
        # Load config to determine backend
        config_file = os.path.join(base_dir, config_path)
        self.backend = "chroma"  # default
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    self.backend = config.get('retrieval', {}).get('backend', 'chroma')
            except:
                pass  # fallback to chroma
        
        self.manifest = load_manifest(base_dir)
        
        # Initialize based on backend (mandatory LangChain integration)
        if self.backend == "langchain" and LANGCHAIN_AVAILABLE:
            self._init_langchain()
        else:
            self._init_chroma()

    def _init_chroma(self):
        """Initialize original Chroma backend"""
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.client = chromadb.PersistentClient(path=os.path.join(self.base_dir, ".chroma"))

    def _init_langchain(self):
        """Initialize LangChain + LlamaIndex + ChromaDB integration (mandatory)"""
        # Initialize LangChain embeddings
        if LANGCHAIN_AVAILABLE:
            self.embeddings = LangChainEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=120)
        else:
            # Fallback to sentence-transformers
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Set up storage directories
        self.persist_directory = os.path.join(self.base_dir, ".langchain_chroma")
        self.llamaindex_directory = os.path.join(self.base_dir, ".llamaindex_storage")
        
        # Initialize storage maps
        self.vectorstores = {}  # tenant -> LangChain vectorstore mapping
        self.llama_indices = {}  # tenant -> LlamaIndex mapping
        
        # Configure LlamaIndex settings if available
        if LLAMAINDEX_AVAILABLE and LANGCHAIN_AVAILABLE:
            Settings.embed_model = LangchainEmbedding(self.embeddings)
            Settings.chunk_size = 700
            Settings.chunk_overlap = 120

    def _ns(self, tenant_id: str) -> str:
        return f"tenant_{tenant_id}"

    def build_or_update(self):
        """Build or update indices - preserves exact function signature"""
        if self.backend == "langchain" and LANGCHAIN_AVAILABLE:
            self._build_langchain()
        else:
            self._build_chroma()

    def _build_chroma(self):
        """Original Chroma implementation"""
        by_tenant = {}
        for row in self.manifest:
            by_tenant.setdefault(row["tenant"], []).append(row)
        for t, rows in by_tenant.items():
            ns = self._ns(t if t!="PUB" else "public")
            coll = self.client.get_or_create_collection(name=ns)
            ids, docs, metas = [], [], []
            for r in rows:
                ids.append(r["doc_id"])
                docs.append(read_doc(self.base_dir, r["path"]))
                vis = "public" if ("PUB_" in r["doc_id"] or r["tenant"]=="PUB") else "private"
                metas.append({"doc_id": r["doc_id"], "tenant": (t if t!="PUB" else "public"), "visibility": vis, "path": r["path"]})
            coll.upsert(ids=ids, documents=docs, metadatas=metas)

    def _build_langchain(self):
        """LangChain + LlamaIndex + ChromaDB implementation (mandatory integration)"""
        by_tenant = {}
        for row in self.manifest:
            by_tenant.setdefault(row["tenant"], []).append(row)

        for tenant, rows in by_tenant.items():
            langchain_documents = []
            llama_documents = []
            
            for row in rows:
                content = read_doc(self.base_dir, row["path"])
                vis = "public" if ("PUB_" in row["doc_id"] or row["tenant"] == "PUB") else "private"
                tenant_name = "public" if row["tenant"] == "PUB" else row["tenant"]
                
                metadata = {
                    "doc_id": row["doc_id"],
                    "tenant": tenant_name,
                    "visibility": vis,
                    "path": row["path"]
                }
                
                # Create LangChain document
                if LANGCHAIN_AVAILABLE:
                    langchain_doc = Document(page_content=content, metadata=metadata)
                    langchain_documents.append(langchain_doc)
                
                # Create LlamaIndex document for support
                if LLAMAINDEX_AVAILABLE:
                    llama_doc = LlamaDocument(text=content, metadata=metadata)
                    llama_documents.append(llama_doc)

            if langchain_documents and LANGCHAIN_AVAILABLE:
                # Create LangChain vectorstore with ChromaDB backend
                tenant_persist_dir = os.path.join(self.persist_directory, self._ns(tenant))
                os.makedirs(tenant_persist_dir, exist_ok=True)
                
                vectorstore = LangChainChroma.from_documents(
                    documents=langchain_documents,
                    embedding=self.embeddings,
                    persist_directory=tenant_persist_dir
                )
                self.vectorstores[tenant] = vectorstore
            
            # Also create LlamaIndex support (for enhanced retrieval if needed)
            if llama_documents and LLAMAINDEX_AVAILABLE and LANGCHAIN_AVAILABLE:
                try:
                    # Create LlamaIndex with ChromaDB backend
                    tenant_llama_dir = os.path.join(self.llamaindex_directory, self._ns(tenant))
                    os.makedirs(tenant_llama_dir, exist_ok=True)
                    
                    # Use existing ChromaDB collection for LlamaIndex
                    chroma_client = chromadb.PersistentClient(path=tenant_persist_dir)
                    chroma_collection = chroma_client.get_or_create_collection(f"{self._ns(tenant)}_llama")
                    
                    vector_store = LlamaChromaStore(chroma_collection=chroma_collection)
                    index = VectorStoreIndex.from_documents(llama_documents, vector_store=vector_store)
                    self.llama_indices[tenant] = index
                    
                except Exception:
                    # LlamaIndex support is optional - continue without it
                    pass

    def search(self, query: str, tenant_id: str, top_k: int = 6) -> List[Hit]:
        """Search using configured backend - preserves exact function signature"""
        if self.backend == "langchain" and LANGCHAIN_AVAILABLE:
            return self._search_langchain(query, tenant_id, top_k)
        else:
            return self._search_chroma(query, tenant_id, top_k)

    def _search_chroma(self, query: str, tenant_id: str, top_k: int = 6) -> List[Hit]:
        """Original Chroma search implementation"""
        hits: list[Hit] = []
        def q(ns):
            try:
                coll = self.client.get_or_create_collection(ns)
                res = coll.query(query_texts=[query], n_results=top_k)
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                dists = res.get("distances", [[]])[0]
                for text, meta, dist in zip(docs, metas, dists):
                    score = 1.0/(1.0+float(dist)) if dist is not None else 0.5
                    hits.append(Hit(meta["doc_id"], meta["tenant"], meta["visibility"], "n/a", text, score))
            except Exception:
                pass  # Collection might not exist, skip silently
        
        # Search all tenant-specific collections that match the pattern
        tenant_patterns = [f"{tenant_id}_genomics", f"{tenant_id}_nlp", f"{tenant_id}_robotics", f"{tenant_id}_materials"]
        for pattern in tenant_patterns:
            q(self._ns(pattern))
        
        # Also search public
        q(self._ns("public"))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    def _search_langchain(self, query: str, tenant_id: str, top_k: int = 6) -> List[Hit]:
        """LangChain + LlamaIndex + ChromaDB search implementation (mandatory integration)"""
        hits: list[Hit] = []

        def search_vectorstore(tenant_key: str):
            # Primary search with LangChain + ChromaDB
            if tenant_key not in self.vectorstores and LANGCHAIN_AVAILABLE:
                # Try to load existing LangChain vectorstore
                tenant_persist_dir = os.path.join(self.persist_directory, self._ns(tenant_key))
                if os.path.exists(tenant_persist_dir):
                    try:
                        vectorstore = LangChainChroma(
                            persist_directory=tenant_persist_dir,
                            embedding_function=self.embeddings
                        )
                        self.vectorstores[tenant_key] = vectorstore
                    except Exception:
                        pass  # Skip if vectorstore doesn't exist

            # Search with LangChain + ChromaDB
            if tenant_key in self.vectorstores:
                try:
                    results = self.vectorstores[tenant_key].similarity_search_with_score(
                        query, k=top_k
                    )
                    
                    for doc, score in results:
                        # Convert to Hit format (preserves exact return type)
                        hit = Hit(
                            doc_id=doc.metadata["doc_id"],
                            tenant=doc.metadata["tenant"],
                            visibility=doc.metadata["visibility"],
                            page="n/a",
                            text=doc.page_content,
                            score=1.0 / (1.0 + float(score)) if score is not None else 0.5
                        )
                        hits.append(hit)
                except Exception:
                    pass

            # Optional LlamaIndex support for enhanced retrieval
            if tenant_key in self.llama_indices and LLAMAINDEX_AVAILABLE:
                try:
                    query_engine = self.llama_indices[tenant_key].as_query_engine(
                        similarity_top_k=min(top_k, 3)  # Use fewer results from LlamaIndex
                    )
                    response = query_engine.query(query)
                    
                    # Add LlamaIndex results (if they provide additional value)
                    if hasattr(response, 'source_nodes'):
                        for node in response.source_nodes[:2]:  # Limit to 2 additional results
                            if hasattr(node, 'metadata') and hasattr(node, 'text'):
                                hit = Hit(
                                    doc_id=node.metadata.get("doc_id", "llama_unknown"),
                                    tenant=node.metadata.get("tenant", tenant_key),
                                    visibility=node.metadata.get("visibility", "private"),
                                    page="n/a",
                                    text=node.text,
                                    score=getattr(node, 'score', 0.3)  # Lower score for LlamaIndex results
                                )
                                # Only add if not already in results
                                if not any(h.doc_id == hit.doc_id and h.text[:100] == hit.text[:100] for h in hits):
                                    hits.append(hit)
                except Exception:
                    pass  # LlamaIndex support is optional

        # Search tenant-specific patterns (preserves exact behavior)
        tenant_patterns = [f"{tenant_id}_genomics", f"{tenant_id}_nlp", f"{tenant_id}_robotics", f"{tenant_id}_materials"]
        for pattern in tenant_patterns:
            search_vectorstore(pattern)
        
        # Also search public
        search_vectorstore("PUB")

        # Sort by score and return top_k (preserves exact behavior)
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]
