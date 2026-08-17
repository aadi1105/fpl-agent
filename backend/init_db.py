import logging
from backend.database import engine, Base, SessionLocal
from backend.ingestion.fpl_api import FPLDataIngestion

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")

def init_database():
    logger.info("Creating database tables if they do not exist...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully.")

def run_sync():
    logger.info("Starting FPL data sync...")
    db = SessionLocal()
    try:
        ingestion = FPLDataIngestion()
        results = ingestion.sync_all(db)
        logger.info(f"FPL sync completed successfully: {results}")
        return results
    except Exception as e:
        logger.error(f"Error during FPL sync: {e}", exc_info=True)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
    run_sync()
