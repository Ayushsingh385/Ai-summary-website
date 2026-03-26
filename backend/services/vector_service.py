from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os

MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_FILE = "faiss_index.bin"

class VectorService:
    def __init__(self):
        # We'll initialize the index as empty first. 
        # The embedding dimension for all-MiniLM-L6-v2 is 384.
        self._model = None
        self.embedding_dim = 384 
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.embedding_dim))
        self.load_index()

    def _get_model(self):
        """Lazy-load the SentenceTransformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            print(f"Loading SentenceTransformer {MODEL_NAME}...")
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    def load_index(self):
        if os.path.exists(INDEX_FILE):
            try:
                self.index = faiss.read_index(INDEX_FILE)
                print(f"Loaded FAISS index with {self.index.ntotal} vectors.")
            except Exception as e:
                print(f"Error loading FAISS index: {e}")

    def save_index(self):
        faiss.write_index(self.index, INDEX_FILE)

    def add_document(self, case_id: int, text: str):
        """Encodes text and adds it to the FAISS index using case_id as the vector ID."""
        model = self._get_model()
        # Truncate to first 2000 chars for semantic memory (efficiency)
        text_preview = text[:2000]
        embedding = model.encode([text_preview], normalize_embeddings=True)
        ids = np.array([case_id], dtype=np.int64)
        self.index.add_with_ids(embedding, ids)
        self.save_index()
        print(f"Added doc {case_id} to FAISS. Total: {self.index.ntotal}")

    def remove_document(self, case_id: int):
        """Removes a document from the FAISS index by case_id."""
        ids = np.array([case_id], dtype=np.int64)
        try:
            self.index.remove_ids(ids)
            self.save_index()
        except Exception as e:
            print(f"Error removing {case_id} from FAISS: {e}")

    def find_similar(self, text: str, top_k: int = 1, threshold: float = 0.65):
        """
        Finds the most similar document to the given text.
        Returns a list of tuples: (case_id, similarity_score)
        """
        if self.index.ntotal == 0:
            return []
            
        model = self._get_model()
        text_preview = text[:2000]
        embedding = model.encode([text_preview], normalize_embeddings=True)
        distances, indices = self.index.search(embedding, top_k)
        
        results = []
        for i in range(len(indices[0])):
            case_id = int(indices[0][i])
            score = float(distances[0][i])
            if case_id != -1 and score >= threshold:
                results.append((case_id, score))
                
        return results

# Singleton instance
vector_service = VectorService()
