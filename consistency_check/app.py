import connexion
from connexion import NoContent
import json
import yaml
import logging
import logging.config
import os
import time
from datetime import datetime
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

# Set environment variable for logging
os.environ["LOG_FILENAME"] = "/app/logs/consistency.log"

# Load logging configuration
with open('/app/config/log_config.yml', 'r') as f:
    log_config = yaml.safe_load(f)
logging.config.dictConfig(log_config)
logger = logging.getLogger("basicLogger")

# Load application configuration
with open('/app/config/consistency_check/consistency_config.yml', 'r') as f:
    app_config = yaml.safe_load(f)

# Define consistency check file path
CONSISTENCY_FILE = app_config['datastore']['filename']


def get_consistency_checks():
    logger.info("GET request received for consistency check results")
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONSISTENCY_FILE), exist_ok=True)
        
        if not os.path.exists(CONSISTENCY_FILE):
            logger.warning("No consistency check file found")
            # Return an empty but valid schema
            return 404

        
        with open(CONSISTENCY_FILE, "r") as f:
            consistency_check = json.load(f)
        
        logger.info("GET request for consistency check results completed")
        return consistency_check, 200
    except Exception as e:
        logger.error(f"Error retrieving consistency check results: {str(e)}")
        return {"message": f"Error: {str(e)}"}, 500

def update_consistency_checks():
    logger.info("Starting consistency check between Kafka queue and storage database")
    start_time = time.time()
    
    try:
        # Get counts from processing
        processing_url = f"{app_config['endpoints']['processing']}/statistics"
        logger.debug(f"Fetching processing statistics from: {processing_url}")
        processing_response = httpx.get(processing_url)
        
        if processing_response.status_code != 200:
            logger.error(f"Failed to get statistics from processing: {processing_response.status_code}")
            return {"message": "Failed to get statistics from processing"}, 500
        
        processing_stats = processing_response.json()
        
        # Get counts and IDs from analyzer (Kafka)
        analyzer_stats_url = f"{app_config['endpoints']['analyzer']}/stats"
        analyzer_race_ids_url = f"{app_config['endpoints']['analyzer']}/race_trace_ids"
        analyzer_telemetry_ids_url = f"{app_config['endpoints']['analyzer']}/telemetry_trace_ids"
        
        logger.debug(f"Fetching analyzer statistics from: {analyzer_stats_url}")
        analyzer_stats_response = httpx.get(analyzer_stats_url)
        if analyzer_stats_response.status_code == 200:
            analyzer_stats = analyzer_stats_response.json()
        else:
            logger.error(f"Failed to fetch analyzer statistics: {analyzer_stats_response.status_code}")
            return {"message": "Failed to fetch analyzer statistics"}, 500
        
        logger.debug(f"Fetching race trace IDs from: {analyzer_race_ids_url}")
        analyzer_race_ids_response = httpx.get(analyzer_race_ids_url)
        
        logger.debug(f"Fetching telemetry trace IDs from: {analyzer_telemetry_ids_url}")
        analyzer_telemetry_ids_response = httpx.get(analyzer_telemetry_ids_url)
        
        if (analyzer_stats_response.status_code != 200 or 
            analyzer_race_ids_response.status_code != 200 or 
            analyzer_telemetry_ids_response.status_code != 200):
            logger.error(f"Failed to get data from analyzer: {analyzer_stats_response.status_code}, {analyzer_race_ids_response.status_code}, {analyzer_telemetry_ids_response.status_code}")
            return {"message": "Failed to get data from analyzer"}, 500

        # Handle Kafka trace ID responses safely
        if analyzer_race_ids_response.status_code != 200 or analyzer_telemetry_ids_response.status_code != 200:
            logger.error("Failed to fetch trace IDs from analyzer (Kafka)")
            return {"message": "Failed to fetch trace IDs from Kafka"}, 500

        race_trace_ids = analyzer_race_ids_response.json()
        telemetry_trace_ids = analyzer_telemetry_ids_response.json()
        
        # Get counts and IDs from storage (database)
        storage_record_count_url = f"{app_config['endpoints']['storage']}/record_count"
        storage_race_ids_url = f"{app_config['endpoints']['storage']}/event_ids"
        storage_telemetry_ids_url = f"{app_config['endpoints']['storage']}/telemetry_ids"
        
        storage_record_count_response = httpx.get(storage_record_count_url)

        storage_race_ids_response = httpx.get(storage_race_ids_url)
        
        storage_telemetry_ids_response = httpx.get(storage_telemetry_ids_url)
        
        if (storage_record_count_response.status_code != 200 or 
            storage_race_ids_response.status_code != 200 or 
            storage_telemetry_ids_response.status_code != 200):
            return {"message": "Failed to get data from storage"}, 500
        
        record_counts = storage_record_count_response.json()
        storage_race_ids = storage_race_ids_response.json()
        storage_telemetry_ids = storage_telemetry_ids_response.json()
        
        # Compare trace IDs to find missing events
        queue_race_trace_ids = {item["trace_id"]: item["event_id"] for item in race_trace_ids}
        queue_telemetry_trace_ids = {item["trace_id"]: item["telemetry_id"] for item in telemetry_trace_ids}
        
        db_race_trace_ids = {item["trace_id"]: item["event_id"] for item in storage_race_ids}
        db_telemetry_trace_ids = {item["trace_id"]: item["telemetry_id"] for item in storage_telemetry_ids}
        
        # Find events missing in database
        missing_in_db = []
        for trace_id, event_id in queue_race_trace_ids.items():
            if trace_id not in db_race_trace_ids:
                missing_in_db.append({
                    "event_id": event_id,
                    "trace_id": trace_id,
                    "type": "race_events"
                })
        
        for trace_id, telemetry_id in queue_telemetry_trace_ids.items():
            if trace_id not in db_telemetry_trace_ids:
                missing_in_db.append({
                    "event_id": telemetry_id,
                    "trace_id": trace_id,
                    "type": "telemetry_data"
                })
        
        # Find events missing in queue
        missing_in_queue = []
        for trace_id, event_id in db_race_trace_ids.items():
            if trace_id not in queue_race_trace_ids:
                missing_in_queue.append({
                    "event_id": event_id,
                    "trace_id": trace_id,
                    "type": "race_events"
                })
        
        for trace_id, telemetry_id in db_telemetry_trace_ids.items():
            if trace_id not in queue_telemetry_trace_ids:
                missing_in_queue.append({
                    "event_id": telemetry_id,
                    "trace_id": trace_id,
                    "type": "telemetry_data"
                })
        
        # Prepare consistency check result
        consistency_check = {
            "last_updated": int(time.time()),
            "counts": {
                "db": {
                    "race_events": record_counts.get("race_events", 0),
                    "telemetry_data": record_counts.get("telemetry_data", 0)
                },
                "queue": {
                    "race_events": analyzer_stats.get("race_events", 0),
                    "telemetry_data": analyzer_stats.get("telemetry_data", 0)
                },
                "processing": {
                    "race_events": processing_stats.get("stat_type_counts", {}).get("race_events", 0),
                    "telemetry_data": processing_stats.get("stat_type_counts", {}).get("telemetry", 0)
                }
            },
            "not_in_db": missing_in_db,
            "not_in_queue": missing_in_queue
        }


        
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONSISTENCY_FILE), exist_ok=True)
        
        # Save consistency check result to file
        with open(CONSISTENCY_FILE, "w") as f:
            json.dump(consistency_check, f, indent=2)
        
        end_time = time.time()
        processing_time_ms = int((end_time - start_time) * 1000)
        
        logger.info(f"Consistency checks completed | processing_time_ms={processing_time_ms} | missing_in_db={len(missing_in_db)} | missing_in_queue={len(missing_in_queue)}")
        
        return {"processing_time_ms": processing_time_ms}, 200
    except Exception as e:
        logger.error(f"Error performing consistency check: {str(e)}")
        return {"message": f"Error: {str(e)}"}, 500

def run_scheduled_check():
    """Run scheduled consistency check"""
    logger.info("Running scheduled consistency check")
    update_consistency_checks()

def init_scheduler():
    """Initialize the scheduler for periodic consistency checks"""
    scheduler = BackgroundScheduler(daemon=True)
    interval = app_config['scheduler']['interval']
    scheduler.add_job(run_scheduled_check, 'interval', seconds=interval)
    scheduler.start()
    logger.info(f"Scheduler started with interval of {interval} seconds")

app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api("./openapi.yml", base_path="/consistency", strict_validation=True, validate_responses=True)

if "CORS_ALLOW_ALL" in os.environ and os.environ["CORS_ALLOW_ALL"] == "yes":    
    app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

if __name__ == "__main__":
    init_scheduler()
    app.run(port=8110, host="0.0.0.0")
