"""
ChromaDB integration for policy document embeddings and semantic search.

This service manages policy document embeddings in ChromaDB for semantic
search and retrieval-augmented generation (RAG) during compliance checking.

References:
- ChromaDB: https://www.trychroma.com/
- vLLM embeddings: https://docs.vllm.ai/
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class ChromaDBConfig:
    """Configuration for ChromaDB connection."""
    host: str = 'localhost'
    port: int = 8000
    collection_name: str = 'ifinbank_policies'
    embedding_model: str = 'all-MiniLM-L6-v2'
    persist_directory: str = './chromadb_data'
    
    @classmethod
    def from_settings(cls) -> 'ChromaDBConfig':
        """Create config from Django settings."""
        return cls(
            host=getattr(settings, 'CHROMADB_HOST', 'localhost'),
            port=getattr(settings, 'CHROMADB_PORT', 8000),
            collection_name=getattr(settings, 'CHROMADB_COLLECTION', 'ifinbank_policies'),
            embedding_model=getattr(settings, 'EMBEDDING_MODEL', 'all-MiniLM-L6-v2'),
            persist_directory=str(getattr(settings, 'CHROMADB_PERSIST_DIR', './chromadb_data')),
        )


@dataclass
class SearchResult:
    """Result of a semantic search query."""
    policy_id: str
    policy_code: str
    content: str
    score: float
    metadata: Dict[str, Any]


class PolicyEmbeddingService:
    """
    Service for managing policy document embeddings in ChromaDB.
    
    This service provides:
    - Policy document indexing with embeddings
    - Semantic search for relevant policies
    - RAG-style context retrieval for compliance checking
    """
    
    def __init__(self, config: ChromaDBConfig = None):
        """
        Initialize the policy embedding service.
        
        Args:
            config: ChromaDBConfig instance (created from settings if None)
        """
        self.config = config or ChromaDBConfig.from_settings()
        self._client = None
        self._collection = None
        self._embedding_function = None
    
    @property
    def client(self):
        """Get or create ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings
                
                # Try persistent client first
                self._client = chromadb.PersistentClient(
                    path=self.config.persist_directory,
                    settings=Settings(anonymized_telemetry=False)
                )
                logger.info(f"ChromaDB connected at {self.config.persist_directory}")
            except ImportError:
                logger.warning("ChromaDB not installed. Using mock client.")
                self._client = MockChromaClient()
            except Exception as e:
                logger.warning(f"ChromaDB connection failed: {e}. Using mock client.")
                self._client = MockChromaClient()
        return self._client
    
    @property
    def embedding_function(self):
        """Get or create embedding function."""
        if self._embedding_function is None:
            try:
                from chromadb.utils import embedding_functions
                
                self._embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.config.embedding_model
                )
            except ImportError:
                logger.warning("Sentence transformers not available. Using mock embeddings.")
                self._embedding_function = MockEmbeddingFunction()
            except Exception as e:
                logger.warning(f"Embedding function creation failed: {e}")
                self._embedding_function = MockEmbeddingFunction()
        return self._embedding_function
    
    @property
    def collection(self):
        """Get or create the policy collection."""
        if self._collection is None:
            try:
                self._collection = self.client.get_or_create_collection(
                    name=self.config.collection_name,
                    embedding_function=self.embedding_function,
                    metadata={'description': 'iFin Bank policy documents for compliance'}
                )
            except Exception as e:
                logger.error(f"Collection creation failed: {e}")
                raise
        return self._collection
    
    def index_policy(
        self,
        policy_id: str,
        policy_code: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Index a policy document in ChromaDB.
        
        Args:
            policy_id: Unique policy identifier
            policy_code: Policy code (e.g., 'KYC-001')
            content: Full policy text content
            metadata: Additional metadata (category, version, etc.)
            
        Returns:
            True if indexing succeeded
        """
        try:
            # Chunk large documents
            chunks = self._chunk_document(content)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{policy_id}_chunk_{i}"
                chunk_metadata = {
                    'policy_id': policy_id,
                    'policy_code': policy_code,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    **(metadata or {})
                }
                
                self.collection.upsert(
                    ids=[chunk_id],
                    documents=[chunk],
                    metadatas=[chunk_metadata]
                )
            
            logger.info(f"Indexed policy {policy_code} with {len(chunks)} chunks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index policy {policy_code}: {e}")
            return False
    
    def remove_policy(self, policy_id: str) -> bool:
        """
        Remove a policy from the index.
        
        Args:
            policy_id: Policy identifier to remove
            
        Returns:
            True if removal succeeded
        """
        try:
            # Find all chunks for this policy
            results = self.collection.get(
                where={'policy_id': policy_id}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Removed policy {policy_id} ({len(results['ids'])} chunks)")
            
            return True
        except Exception as e:
            logger.error(f"Failed to remove policy {policy_id}: {e}")
            return False
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        category: str = None,
        min_score: float = 0.0
    ) -> List[SearchResult]:
        """
        Semantic search for relevant policies.
        
        Args:
            query: Search query text
            n_results: Maximum number of results
            category: Optional category filter
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of SearchResult objects
        """
        try:
            # Build filter if category specified
            where = {'category': category} if category else None
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=['documents', 'metadatas', 'distances']
            )
            
            search_results = []
            
            if results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    # ChromaDB returns L2 distance, convert to similarity
                    distance = results['distances'][0][i] if results['distances'] else 0
                    score = 1 / (1 + distance)  # Convert distance to similarity
                    
                    if score >= min_score:
                        metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                        search_results.append(SearchResult(
                            policy_id=metadata.get('policy_id', ''),
                            policy_code=metadata.get('policy_code', ''),
                            content=results['documents'][0][i] if results['documents'] else '',
                            score=score,
                            metadata=metadata
                        ))
            
            logger.debug(f"Semantic search returned {len(search_results)} results for: {query[:50]}...")
            return search_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def find_applicable_policies(
        self,
        verification_context: Dict[str, Any],
        n_results: int = 10
    ) -> List[SearchResult]:
        """
        Find policies applicable to a verification context.
        
        This builds a query from the verification context to find
        relevant compliance policies.
        
        Args:
            verification_context: Dict with customer data, document types, etc.
            n_results: Maximum results to return
            
        Returns:
            List of relevant policy SearchResults
        """
        # Build contextual query
        query_parts = []
        
        # Account type context
        account_type = verification_context.get('account_type', 'savings')
        query_parts.append(f"{account_type} account opening requirements")
        
        # Document types
        doc_types = verification_context.get('document_types', [])
        if doc_types:
            query_parts.append(f"verification of {', '.join(doc_types)}")
        
        # Customer category (individual, corporate, etc.)
        customer_type = verification_context.get('customer_type', 'individual')
        query_parts.append(f"KYC requirements for {customer_type} customers")
        
        query = '. '.join(query_parts)
        
        return self.search(query, n_results=n_results)
    
    def get_compliance_context(
        self,
        check_type: str,
        n_results: int = 3
    ) -> str:
        """
        Get policy context for a specific compliance check type.
        
        Used for RAG-style context injection during compliance evaluation.
        
        Args:
            check_type: Type of check (e.g., 'kyc_id_verification', 'aml_screening')
            n_results: Number of policy excerpts to retrieve
            
        Returns:
            Concatenated policy context string
        """
        # Map check types to queries
        check_queries = {
            'kyc_id_verification': 'identity document verification requirements proof of identity',
            'kyc_required_fields': 'required customer information fields KYC data collection',
            'kyc_age_verification': 'minimum age requirements account eligibility age restrictions',
            'aml_watchlist': 'AML sanctions screening watchlist checking OFAC UN',
            'aml_pep_check': 'politically exposed persons PEP identification enhanced due diligence',
            'document_quality': 'document quality standards legibility requirements image quality',
        }
        
        query = check_queries.get(check_type, check_type)
        results = self.search(query, n_results=n_results, min_score=0.3)
        
        if not results:
            return ''
        
        # Combine relevant policy excerpts
        context_parts = []
        for result in results:
            context_parts.append(
                f"[Policy {result.policy_code}]: {result.content}"
            )
        
        return '\n\n'.join(context_parts)
    
    def sync_all_policies(self) -> Tuple[int, int]:
        """
        Sync all active policies from database to ChromaDB.
        
        Returns:
            Tuple of (indexed_count, failed_count)
        """
        from apps.compliance.models import Policy
        
        indexed = 0
        failed = 0
        
        policies = Policy.objects.filter(is_active=True)
        
        for policy in policies:
            metadata = {
                'category': policy.category,
                'version': policy.version,
                'effective_date': str(policy.effective_date),
                'name': policy.name,
            }
            
            success = self.index_policy(
                policy_id=str(policy.id),
                policy_code=policy.code,
                content=policy.content,
                metadata=metadata
            )
            
            if success:
                # Update policy with embedding ID
                policy.embedding_id = str(policy.id)
                policy.save(update_fields=['embedding_id'])
                indexed += 1
            else:
                failed += 1
        
        logger.info(f"Policy sync complete: {indexed} indexed, {failed} failed")
        return indexed, failed
    
    def _chunk_document(
        self,
        content: str,
        max_chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        """
        Split document into overlapping chunks for better embedding coverage.
        
        Args:
            content: Document content
            max_chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks
            
        Returns:
            List of document chunks
        """
        if len(content) <= max_chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + max_chunk_size
            
            # Try to break at sentence boundary
            if end < len(content):
                # Look for period, newline, or space
                for delimiter in ['. ', '\n', ' ']:
                    boundary = content.rfind(delimiter, start + max_chunk_size // 2, end)
                    if boundary > start:
                        end = boundary + len(delimiter)
                        break
            
            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
        
        return chunks
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the policy collection."""
        try:
            count = self.collection.count()
            return {
                'total_documents': count,
                'collection_name': self.config.collection_name,
                'embedding_model': self.config.embedding_model,
            }
        except Exception as e:
            return {'error': str(e)}


class MockChromaClient:
    """Mock ChromaDB client for development without ChromaDB installed."""
    
    def __init__(self):
        self._collections = {}
    
    def get_or_create_collection(self, name, **kwargs):
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]


class MockCollection:
    """Mock ChromaDB collection."""
    
    def __init__(self, name):
        self.name = name
        self._documents = {}
    
    def upsert(self, ids, documents, metadatas=None):
        for i, doc_id in enumerate(ids):
            self._documents[doc_id] = {
                'document': documents[i],
                'metadata': metadatas[i] if metadatas else {}
            }
    
    def get(self, where=None):
        ids = []
        for doc_id, doc in self._documents.items():
            if where:
                match = all(doc['metadata'].get(k) == v for k, v in where.items())
                if match:
                    ids.append(doc_id)
            else:
                ids.append(doc_id)
        return {'ids': ids}
    
    def delete(self, ids):
        for doc_id in ids:
            self._documents.pop(doc_id, None)
    
    def query(self, query_texts, n_results=5, where=None, include=None):
        # Simple mock that returns first n_results
        docs = list(self._documents.items())[:n_results]
        return {
            'ids': [[d[0] for d in docs]],
            'documents': [[d[1]['document'] for d in docs]],
            'metadatas': [[d[1]['metadata'] for d in docs]],
            'distances': [[0.5] * len(docs)],
        }
    
    def count(self):
        return len(self._documents)


class MockEmbeddingFunction:
    """Mock embedding function for development."""
    
    def __call__(self, texts):
        # Return random-ish embeddings
        import hashlib
        embeddings = []
        for text in texts:
            # Create deterministic pseudo-embedding from text hash
            hash_bytes = hashlib.md5(text.encode()).digest()
            embedding = [float(b) / 255.0 for b in hash_bytes[:16]] * 24
            embeddings.append(embedding[:384])  # 384-dim like all-MiniLM-L6-v2
        return embeddings


# Singleton instance
_embedding_service: Optional[PolicyEmbeddingService] = None


def get_embedding_service() -> PolicyEmbeddingService:
    """Get or create the singleton embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = PolicyEmbeddingService()
    return _embedding_service
