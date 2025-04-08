import connexion
from connexion import NoContent
import json
import logging
import logging.config
import yaml
from pykafka import KafkaClient
import os
import time
from datetime import datetime
import httpx
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
os.environ["LOG_FILENAME"] = "/app/logs/analyzer.log"

# Load logging configuration
with open("/app/config/log_config.yml", "r") as f:
    log_config = yaml.safe_load(f)
logging.config.dictConfig(log_config)
logger = logging.getLogger("basicLogger")

# Load application configuration
with open("/app/config/analyzer/analyzer_config.yml", "r") as f:
    app_config = yaml.safe_load(f)

# Define consistency check file path
CONSISTENCY_FILE = "/app/data/consistency_check.json"

def get_telemetry_index(index):
    logger.info(f"Fetching telemetry data at index {index}")
    client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    topic = client.topics[app_config['events']['topic'].encode()]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)

    counter = 0
    for msg in consumer:
        msg_str = msg.value.decode("utf-8")
        msg = json.loads(msg_str)
        if msg["type"] == "telemetry_data" and counter == index:
            logger.info(f"Telemetry data found at index {index}")
            return msg["payload"], 200
        if msg["type"] == "telemetry_data":
            counter += 1
    logger.warning(f"Telemetry data not found at index {index}")
    return {"message": "Not Found"}, 404

def get_race_event_index(index):
    logger.info(f"Fetching race event at index {index}")
    client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    topic = client.topics[app_config['events']['topic'].encode()]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    counter = 0
    for msg in consumer:
        msg_str = msg.value.decode("utf-8")
        msg = json.loads(msg_str)
        logger.debug(f"Consumed message: {msg}")
        if msg["type"] == "race_events" and counter == index:
            logger.info(f"Race event found at index {index}")
            return msg["payload"], 200
        if msg["type"] == "race_events":
            counter += 1
    logger.warning(f"Race event not found at index {index}")
    return {"message": "Not Found"}, 404

def get_stats():
    logger.info("Fetching statistics")

    client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    
    telemetry_topic = client.topics[app_config['events']['topic'].encode()]
    telemetry_consumer = telemetry_topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    telemetry_count = sum(1 for msg in telemetry_consumer if msg and json.loads(msg.value.decode("utf-8"))["type"] == "telemetry_data")
    
    race_topic = client.topics[app_config['events']['topic'].encode()]
    race_consumer = race_topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    race_count = sum(1 for msg in race_consumer if msg and json.loads(msg.value.decode("utf-8"))["type"] == "race_events")
    
    logger.info("Statistics fetched successfully")
    return {
        "telemetry_data": telemetry_count,
        "race_events": race_count
    }, 200

def get_telemetry_trace_ids():
    """Get list of telemetry IDs and trace IDs from Kafka"""
    logger.info("GET request received for telemetry trace IDs from Kafka")
    
    try:
        client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
        topic = client.topics[app_config['events']['topic'].encode()]
        consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
        
        results = []
        for msg in consumer:
            if msg:
                msg_str = msg.value.decode("utf-8")
                msg_data = json.loads(msg_str)
                if msg_data["type"] == "telemetry_data" and "payload" in msg_data:
                    payload = msg_data["payload"]
                    if "telemetry_id" in payload and "trace_id" in payload:
                        results.append({
                            "telemetry_id": payload["telemetry_id"],
                            "trace_id": payload["trace_id"]
                        })
        
        logger.debug(f"Retrieved {len(results)} telemetry trace IDs from Kafka")
        logger.info("GET request for telemetry trace IDs completed")
        
        return results, 200
    except Exception as e:
        logger.error(f"Error retrieving telemetry trace IDs from Kafka: {str(e)}")
        return {"message": f"Error: {str(e)}"}, 500

def get_race_trace_ids():
    """Get list of race event IDs and trace IDs from Kafka"""
    logger.info("GET request received for race event trace IDs from Kafka")
    
    try:
        client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
        topic = client.topics[app_config['events']['topic'].encode()]
        consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
        
        results = []
        for msg in consumer:
            if msg:
                msg_str = msg.value.decode("utf-8")
                msg_data = json.loads(msg_str)
                if msg_data["type"] == "race_events" and "payload" in msg_data:
                    payload = msg_data["payload"]
                    if "event_id" in payload and "trace_id" in payload:
                        results.append({
                            "event_id": payload["event_id"],
                            "trace_id": payload["trace_id"]
                        })
        
        logger.debug(f"Retrieved {len(results)} race event trace IDs from Kafka")
        logger.info("GET request for race event trace IDs completed")
        
        return results, 200
    except Exception as e:
        logger.error(f"Error retrieving race event trace IDs from Kafka: {str(e)}")
        return {"message": f"Error: {str(e)}"}, 500

def update_consistency_check():
    """Perform consistency check between Kafka queue and storage database"""
    logger.info("Starting consistency check between Kafka queue and storage database")
    start_time = time.time()
    
    try:
        # Get counts from processing
        processing_response = httpx.get(f"{app_config['endpoints']['processing']}/statistics")
        if processing_response.status_code != 200:
            logger.error(f"Failed to get statistics from processing: {processing_response.status_code}")
            return {"message": "Failed to get statistics from processing"}, 500
        processing_stats = processing_response.json()
        
        # Get counts and IDs from analyzer (Kafka)
        race_trace_ids_response = get_race_trace_ids()
        telemetry_trace_ids_response = get_telemetry_trace_ids()
        
        race_trace_ids = race_trace_ids_response[0] if race_trace_ids_response[1] == 200 else []
        telemetry_trace_ids = telemetry_trace_ids_response[0] if telemetry_trace_ids_response[1] == 200 else []
        
        # Get counts and IDs from storage (database)
        storage_race_ids_response = httpx.get(f"{app_config['endpoints']['storage']}/event_ids")
        storage_telemetry_ids_response = httpx.get(f"{app_config['endpoints']['storage']}/telemetry_ids")
        
        if storage_race_ids_response.status_code != 200 or storage_telemetry_ids_response.status_code != 200:
            logger.error(f"Failed to get IDs from storage: {storage_race_ids_response.status_code}, {storage_telemetry_ids_response.status_code}")
            return {"message": "Failed to get IDs from storage"}, 500
        
        storage_race_ids = storage_race_ids_response.json()
        storage_telemetry_ids = storage_telemetry_ids_response.json()
        
        # Get record counts
        record_count_response = httpx.get(f"{app_config['endpoints']['storage']}/record_count")
        if record_count_response.status_code != 200:
            logger.error(f"Failed to get record count from storage: {record_count_response.status_code}")
            return {"message": "Failed to get record count from storage"}, 500
        
        record_counts = record_count_response.json()
        
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
            "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "counts": {
                "db": {
                    "race_events": record_counts.get("race_events", 0),
                    "telemetry_data": record_counts.get("telemetry_data", 0)
                },
                "queue": {
                    "race_events": len(race_trace_ids),
                    "telemetry_data": len(telemetry_trace_ids)
                },
                "processing": {
                    "race_events": processing_stats.get("stat_type_counts", {}).get("race_events", 0),
                    "telemetry_data": processing_stats.get("stat_type_counts", {}).get("telemetry", 0)
                }
            },
            "missing_in_db": missing_in_db,
            "missing_in_queue": missing_in_queue
        }
        
        # Save consistency check result to file
        os.makedirs(os.path.dirname(CONSISTENCY_FILE), exist_ok=True)
        with open(CONSISTENCY_FILE, "w") as f:
            json.dump(consistency_check, f, indent=2)
        
        end_time = time.time()
        processing_time_ms = int((end_time - start_time) * 1000)
        
        logger.info(f"Consistency checks completed | processing_time_ms={processing_time_ms} | missing_in_db={len(missing_in_db)} | missing_in_queue={len(missing_in_queue)}")
        
        return {"processing_time_ms": processing_time_ms}, 200
    except Exception as e:
        logger.error(f"Error performing consistency check: {str(e)}")
        return {"message": f"Error: {str(e)}"}, 500

def get_consistency_check():
    """Get results of the latest consistency check"""
    logger.info("GET request received for consistency check results")
    
    try:
        if not os.path.exists(CONSISTENCY_FILE):
            logger.warning("No consistency check file found")
            return {"message": "No consistency checks have been run yet"}, 404
        
        with open(CONSISTENCY_FILE, "r") as f:
            consistency_check = json.load(f)
        
        logger.info("GET request for consistency check results completed")
        return consistency_check, 200
    except Exception as e:
        logger.error(f"Error retrieving consistency check results: {str(e)}")
        return {"message": f"Error: {str(e)}"}, 500
    
app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api("./openapi.yml", base_path="/analyzer", strict_validation=True, validate_responses=True)

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
    app.run(port=8100, host="0.0.0.0")
