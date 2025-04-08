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
logger.debug(f"Loaded config: {json.dumps(app_config, indent=2)}")

# Define consistency check file path
CONSISTENCY_FILE = "./consistency_check.json"  # Changed to a relative path

def get_telemetry_index(index):
    logger.info(f"Fetching telemetry data at index {index}")
    client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    topic = client.topics[app_config['events']['topic'].encode()]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)

    try:
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
    finally:
        consumer.stop()  # Explicitly stop the consumer to ensure cleanup

def get_race_event_index(index):
    logger.info(f"Fetching race event at index {index}")
    client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    topic = client.topics[app_config['events']['topic'].encode()]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)

    try:
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
    finally:
        consumer.stop()  # Explicitly stop the consumer to ensure cleanup

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
    logger.info("POST request received to update consistency check")
    start_time = time.time()

    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(CONSISTENCY_FILE), exist_ok=True)

        # Fetch counts and IDs from processing
        processing_response = httpx.get("http://processing:8091/processing/statistics")
        processing_response.raise_for_status()
        processing_data = processing_response.json()

        # Fetch counts and IDs from analyzer
        analyzer_response = httpx.get("http://localhost:8100/analyzer/trace_ids")
        analyzer_response.raise_for_status()
        analyzer_data = analyzer_response.json()

        # Fetch counts and IDs from storage
        storage_response = httpx.get("http://storage:/storage:8090/storage/trace_ids")
        storage_response.raise_for_status()
        storage_data = storage_response.json()

        # Compare IDs between analyzer and storage
        analyzer_ids = {item["trace_id"] for item in analyzer_data}
        storage_ids = {item["trace_id"] for item in storage_data}

        missing_in_db = list(analyzer_ids - storage_ids)
        missing_in_queue = list(storage_ids - analyzer_ids)

        # Prepare consistency check results
        consistency_check = {
            "last_updated": int(time.time()),
            "missing_in_db": missing_in_db,
            "missing_in_queue": missing_in_queue,
            "processing_counts": processing_data
        }

        # Save results to file
        with open(CONSISTENCY_FILE, "w") as f:
            json.dump(consistency_check, f, indent=4)

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log summary
        logger.info(
            f"Consistency checks completed | processing_time_ms={processing_time_ms} | "
            f"missing_in_db={len(missing_in_db)} | missing_in_queue={len(missing_in_queue)}"
        )

        return {"processing_time_ms": processing_time_ms}, 200

    except Exception as e:
        logger.error(f"Error during consistency check update: {str(e)}")
        return {"message": f"Error: {str(e)}"}, 500

def get_consistency_check():
    """Get results of the latest consistency check"""
    logger.info("GET request received for consistency check results")
    
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(CONSISTENCY_FILE), exist_ok=True)

        if not os.path.exists(CONSISTENCY_FILE):
            logger.warning("No consistency check file found. Creating a new one.")
            # Create an empty consistency check file
            consistency_check = {
                "last_updated": None,
                "missing_in_db": [],
                "missing_in_queue": [],
                "processing_counts": {}
            }
            with open(CONSISTENCY_FILE, "w") as f:
                json.dump(consistency_check, f, indent=4)
            return consistency_check, 200
        
        with open(CONSISTENCY_FILE, "r") as f:
            consistency_check = json.load(f)
        
        # Ensure last_updated is a valid string or set a default value
        if consistency_check["last_updated"] is None:
            consistency_check["last_updated"] = "1970-01-01T00:00:00Z"
        
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
