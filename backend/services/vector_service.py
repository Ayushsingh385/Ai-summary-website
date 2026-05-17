from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_FILE = "faiss_index.bin"
CHUNK_SIZE = 1000  # Characters per chunk
CHUNK_OVERLAP = 100 # Overlap to prevent context clipping at boundaries

class VectorService:
    def __init__(self):
        self._model = None
        self.embedding_dim = 384 
        # Using IndexFlatIP for inner product (cosine similarity if normalized)
        # We use IndexIDMap to allow specific case_id mapping
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.embedding_dim))
        self.load_index()

    def _get_model(self):
        """Lazy-load the SentenceTransformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"Loading SentenceTransformer {MODEL_NAME} on {device}...")
            self._model = SentenceTransformer(MODEL_NAME, device=device)
        return self._model

    def load_index(self):
        if os.path.exists(INDEX_FILE):
            try:
                self.index = faiss.read_index(INDEX_FILE)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors.")
            except Exception as e:
                logger.error(f"Error loading FAISS index: {e}")

    def save_index(self):
        faiss.write_index(self.index, INDEX_FILE)

    def _chunk_text(self, text: str):
        """Splits text into overlapping chunks to maintain context."""
        chunks = []
        for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP):
            chunks.append(text[i : i + CHUNK_SIZE])
        return chunks

    def add_document(self, case_id: int, text: str):
        """
        Encodes text using a sliding window approach and adds multiple 
        vectors per document to the FAISS index.
        """
        if not text:
            return

        model = self._get_model()
        chunks = self._chunk_text(text)
        
        # Generate embeddings for all chunks
        embeddings = model.encode(chunks, normalize_embeddings=True)
        
        # Since IndexIDMap requires unique IDs for every vector, but we want 
        # all chunks to map to the same case_id, we actually need to store 
        # the vectors and handle the mapping. 
        # FIX: FAISS IndexIDMap requires UNIQUE IDs. 
        # To solve this, we'll use a composite ID: case_id * 100 + chunk_index
        # Or better: use the standard index and keep a mapping file.
        # For this implementation, we will use composite IDs to keep it in one file.
        
        composite_ids = np.array([case_id * 1000 + idx for idx in range(len(chunks))], dtype=np.int64)
        
        self.index.add_with_ids(np.array(embeddings), composite_ids)
        self.save_index()
        logger.info(f"Added {len(chunks)} chunks for doc {case_id}. Total vectors: {self.index.ntotal}")

    def remove_document(self, case_id: int):
        """Removes all chunks associated with a document by case_id."""
        try:
            # Use faiss.vector_to_array to read the internal ID map
            id_map = faiss.vector_to_array(self.index.id_map)
            target_ids = np.array([int(uid) for uid in id_map if uid // 1000 == case_id], dtype=np.int64)
        except Exception as e:
            logger.warning(f"Could not read FAISS id_map for removal: {e}")
            target_ids = np.array([], dtype=np.int64)
        
        if len(target_ids) > 0:
            self.index.remove_ids(target_ids)
            self.save_index()
            logger.info(f"Removed {len(target_ids)} chunks for doc {case_id}.")

    def find_similar(self, text: str, top_k: int = 5, threshold: float = 0.65):
        """
        Finds the most similar chunks across the database.
        Returns a list of tuples: (case_id, similarity_score)
        """
        if self.index.ntotal == 0:
            return []
            
        model = self._get_model()
        # We embed the query as one vector
        embedding = model.encode([text], normalize_embeddings=True)
        distances, indices = self.index.search(embedding, top_k)
        
        results = []
        for i in range(len(indices[0])):
            composite_id = int(indices[0][i])
            score = float(distances[0][i])
            if composite_id != -1 and score >= threshold:
                case_id = composite_id // 1000 # Recover original case_id
                results.append((case_id, score))
                
        # Deduplicate: if multiple chunks from same case match, keep only the best score
        unique_results = {}
        for case_id, score in results:
            if case_id not in unique_results or score > unique_results[case_id]:
                unique_results[case_id] = score
        
        final_results = sorted(
            [(cid, s) for cid, s in unique_results.items()], 
            key=lambda x: x[1], 
            reverse=True
        )
                
        return final_results

# Singleton instance
vector_service = VectorService()
