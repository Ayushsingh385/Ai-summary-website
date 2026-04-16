import os
import sys
import logging
import time
from sqlalchemy.orm import Session

# Add the parent directory (backend) to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal, engine
import models
from services.pdf_service import extract_text_from_pdf
from services.nlp_service import summarize_text, extract_keywords, compute_text_stats, classify_case_type
from services.vector_service import vector_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants - checking multiple possible locations
POTENTIAL_FOLDERS = [
    r"D:\project_NLP\ZP_Case_Letters",
    r"C:\Vs code\New folder\ZP_Case_Letters",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ZP_Case_Letters"))
]

CASE_FOLDER = next((f for f in POTENTIAL_FOLDERS if os.path.exists(f)), None)

SUMMARIZATION_LENGTH = "medium"
LANGUAGE = "en"

def ingest_cases():
    # Ensure database tables exist
    models.Base.metadata.create_all(bind=engine)
    
    if not os.path.exists(CASE_FOLDER):
        logger.error(f"Case folder not found: {CASE_FOLDER}")
        return

    files = [f for f in os.listdir(CASE_FOLDER) if f.lower().endswith('.pdf')]
    total_files = len(files)
    logger.info(f"Found {total_files} PDF files for ingestion.")

    db: Session = SessionLocal()
    
    processed_count = 0
    error_count = 0

    try:
        for idx, filename in enumerate(files):
            file_path = os.path.join(CASE_FOLDER, filename)
            logger.info(f"[{idx+1}/{total_files}] Processing: {filename}")
            
            try:
                # 1. Read file bytes
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                
                # 2. Extract Text
                extraction_result = extract_text_from_pdf(file_bytes)
                original_text = extraction_result["text"]
                
                if not original_text or len(original_text.strip()) < 50:
                    logger.warning(f"Skipping {filename}: Text too short or extraction failed.")
                    continue

                # 3. Use BART for Summarization
                # This is the "heavy" part
                summary_result = summarize_text(original_text, length=SUMMARIZATION_LENGTH, language=LANGUAGE)
                summary_text = summary_result["summary"]
                
                # 4. Extract Keywords & Stats
                keywords_result = extract_keywords(original_text)
                stats = compute_text_stats(original_text)
                # Add summary stats
                stats["summary_word_count"] = summary_result.get("summary_word_count", 0)
                stats["compression_ratio"] = summary_result.get("compression_ratio", 0)

                # 5. Save to Database
                new_case = models.CaseDocument(
                    filename=filename,
                    original_text=original_text,
                    summary_text=summary_text,
                    keywords=keywords_result,
                    stats=stats
                )
                db.add(new_case)
                db.commit()
                db.refresh(new_case)

                # 6. Add to Vector Index
                vector_service.add_document(new_case.id, original_text)
                
                processed_count += 1
                logger.info(f"Successfully ingested {filename} (ID: {new_case.id})")
                
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                db.rollback()
                error_count += 1
                continue

        logger.info(f"\nIngestion Complete!")
        logger.info(f"Total files: {total_files}")
        logger.info(f"Successfully processed: {processed_count}")
        logger.info(f"Errors: {error_count}")

    finally:
        db.close()

if __name__ == "__main__":
    start_time = time.time()
    ingest_cases()
    end_time = time.time()
    duration = end_time - start_time
    print(f"\n--- Total execution time: {duration:.2f} seconds ---")
