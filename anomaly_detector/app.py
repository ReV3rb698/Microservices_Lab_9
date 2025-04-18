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
from pykafka import KafkaClient

# Set environment variable for logging
os.environ["LOG_FILENAME"] = "/app/logs/anomaly_detector.log"
MAX_LAP_COUNT = int(os.getenv("MAX_LAP_COUNT", 78)) 
MIN_SPEED = int(os.getenv("MIN_SPEED", 0)) 
# Load logging configuration
with open('/app/config/log_config.yml', 'r') as f:
    log_config = yaml.safe_load(f)
logging.config.dictConfig(log_config)
logger = logging.getLogger("basicLogger")

# Load application configuration
with open('/app/config/anomaly_detector/anomaly_config.yml', 'r') as f:
    app_config = yaml.safe_load(f)

# Define consistency check file path
ANOMALY_FILE = app_config['datastore']['filename']
client = KafkaClient(hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
topic = client.topics[app_config['events']['topic'].encode()]

def update_anomalies():
    logger.debug("Updating anomalies")
    start_time = time.perf_counter_ns()
    
    anomalies_to_save = {}
    anomaly_payload = {
            "event_id": "0",
            "trace_id": "0",
            "event_type": "None",
            "anomaly_type": "None",
            "description": "None" 
    }
    consumer = None 
    try:
        consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
        anomaly_payload = {"anomalies_count": 0}
        counter = 0
        for msg in consumer:
            msg_str = msg.value.decode("utf-8")
            msg = json.loads(msg_str)
            if msg["type"] == "telemetry_data" and msg["payload"]["min_speed"] < MIN_SPEED:
                logger.debug(f"anomaly detected, {msg['payload']['min_speed']} is below {MIN_SPEED}")
                anomaly_to_save = anomaly_payload
                anomaly_to_save["event_id"] = msg["payload"]["event_id"]
                anomaly_to_save["trace_id"] = msg["payload"]["trace_id"]
                anomaly_to_save["event_type"] = msg["type"]
                anomaly_to_save["anomaly_type"] = "Out of range speed telemetry"
                anomaly_to_save["description"] = "Speed has been sent as negative"
                anomalies_to_save[counter] = anomaly_to_save
                counter += 1
                
            if msg["type"] == "race_event" and msg["payload"]["lap_number"] > MAX_LAP_COUNT:
                logger.debug(f"anomaly detected, {msg['payload']['lap_number']} is above {MAX_LAP_COUNT}")
                anomaly_to_save = anomaly_payload
                anomaly_to_save["event_id"] = msg["payload"]["event_id"]
                anomaly_to_save["trace_id"] = msg["payload"]["trace_id"]
                anomaly_to_save["event_type"] = msg["type"]
                anomaly_to_save["anomaly_type"] = "Out of range: lap count"
                anomaly_to_save["description"] = "Lap count was sent as too high (over 78)"
                anomalies_to_save[counter] = anomaly_to_save
                counter += 1
        anomaly_payload["anomalies_count"] = counter
        end_time = time.perf_counter_ns()
        total_time = (end_time - start_time) * 1000
        logger.info(f"Update took {total_time} ms")
        with open(ANOMALY_FILE, "w") as f:
            json.dump(anomalies_to_save, f, indent=2)
        return anomaly_payload, 200
    except Exception as e:
        logger.error(f"Error in update_anomalies: {e}")
        return {"msg": "Error occurred while updating anomalies"}, 500
    finally:
        if consumer:
            consumer.stop()


def get_anomalies(event_type=None):
    logger.debug("Getting anomalies..")
    valid_types = ["race_event", "telemetry_event"]
    try:
        with open(ANOMALY_FILE, "r") as f:
                payload_to_return = json.load(f)
    except Exception:
        return {"msg": "Error with opening the json"},404
        
    if event_type not in valid_types and event_type != None:
        return {"msg":"Need to put a valid variable!"},400
    if len(payload_to_return) == 0:
        logger.debug(f"Anomalies retreived: {len(payload_to_return)} ")
        return {"msg": "No anomalies found"},204
    if event_type == "race_event":
        for i in payload_to_return:
            if i["event_type"] == "telemetry_event":
                payload_to_return.pop(i)
        logger.debug(f"Anomalies retreived: {len(payload_to_return)} ")
        return payload_to_return, 200
    elif event_type == "telemetry_event":
        for i in payload_to_return:
            if i["event_type"] == "race_event":
                payload_to_return.pop(i)
        logger.debug(f"Anomalies retreived: {len(payload_to_return)} ")
        return payload_to_return, 200
    else:
        logger.debug(f"Anomalies retreived: {len(payload_to_return)} ")
        return payload_to_return, 200
    
app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api("./openapi.yml", base_path="/anomaly_detector", strict_validation=True, validate_responses=True)

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
    logger.info("Starting on port 8300")
    app.run(port=8300, host="0.0.0.0")