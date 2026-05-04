import os
import sys
import logging
import time
import asyncio
from sqlalchemy.orm import Session

# Add the parent directory (backend) to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal, engine
import models
from services.pdf_service import extract_text_from_pdf
from services.nlp_service import summarize_text, extract_keywords, compute_text_stats, classify_case_type
from services.vector_service import vector_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ingestion.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def ingest_batch(folder_path, skip_existing=True):
    # Ensure database tables exist
    models.Base.metadata.create_all(bind=engine)
    
    if not os.path.exists(folder_path):
        logger.error(f"Folder not found: {folder_path}")
        return

    files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    total_files = len(files)
    logger.info(f"Found {total_files} PDF files in {folder_path}")

    db: Session = SessionLocal()
    
    processed_count = 0
    error_count = 0
    skipped_count = 0

    try:
        # Get existing filenames to avoid duplicates
        existing_filenames = set()
        if skip_existing:
            results = db.query(models.CaseDocument.filename).all()
            existing_filenames = {r[0] for r in results}
            logger.info(f"Loaded {len(existing_filenames)} existing filenames from DB.")

        for idx, filename in enumerate(files):
            if skip_existing and filename in existing_filenames:
                logger.info(f"[{idx+1}/{total_files}] Skipping existing: {filename}")
                skipped_count += 1
                continue

            file_path = os.path.join(folder_path, filename)
            logger.info(f"[{idx+1}/{total_files}] Processing: {filename}")
            
            try:
                # 1. Read file bytes
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                
                # 2. Extract Text (Async call)
                extraction_result = asyncio.run(extract_text_from_pdf(file_bytes))
                original_text = extraction_result["text"]
                
                if not original_text or len(original_text.strip()) < 50:
                    logger.warning(f"Skipping {filename}: Text too short or extraction failed.")
                    continue

                # 3. Summarization (uses Gemini with local fallback)
                summary_result = summarize_text(original_text, length="medium")
                summary_text = summary_result["summary"]
                
                # 4. Keywords, Stats, Classification
                keywords_result = extract_keywords(original_text)
                stats = compute_text_stats(original_text)
                stats["summary_word_count"] = summary_result.get("summary_word_count", 0)
                stats["compression_ratio"] = summary_result.get("compression_ratio", 0)
                
                case_type_result = classify_case_type(original_text)

                # 5. Save to Database
                new_case = models.CaseDocument(
                    filename=filename,
                    original_text=original_text,
                    summary_text=summary_text,
                    keywords=keywords_result,
                    stats=stats,
                    case_type=case_type_result,
                    status="processed"
                )
                db.add(new_case)
                db.commit()
                db.refresh(new_case)

                # 6. Add to Vector Index
                vector_service.add_document(new_case.id, original_text)
                
                processed_count += 1
                logger.info(f"Successfully ingested {filename} (ID: {new_case.id})")
                
                # Small sleep to avoid aggressive CPU usage or API flooding
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                db.rollback()
                error_count += 1
                continue

        logger.info(f"\nBatch Ingestion Complete!")
        logger.info(f"Total files: {total_files}")
        logger.info(f"Processed: {processed_count}")
        logger.info(f"Skipped: {skipped_count}")
        logger.info(f"Errors: {error_count}")

    finally:
        db.close()

if __name__ == "__main__":
    # Use command line arg or default to Strictly Unique folder
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ZP_Strictly_Unique_Cases"))
    
    print(f"Starting Batch Ingestion for: {folder}")
    start_time = time.time()
    ingest_batch(folder)
    end_time = time.time()
    print(f"\n--- Total execution time: {end_time - start_time:.2f} seconds ---")
