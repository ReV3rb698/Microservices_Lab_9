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
        
        return results, 200
    except Exception as e:
        logger.error(f"Error retrieving telemetry trace IDs from Kafka: {str(e)}")
        return {"message": f"Error: {str(e)}"}, 500

def get_race_trace_ids():
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
