import connexion
from connexion import NoContent
from datetime import datetime
import uuid
import time
import yaml
import logging
import logging.config
from pykafka import KafkaClient
import json
import os
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

os.environ["LOG_FILENAME"] = "/app/logs/receiver.log"
with open('/app/config/log_config.yml', 'r') as f:
    log_config = yaml.safe_load(f)
logging.config.dictConfig(log_config)
logger = logging.getLogger("basicLogger")

with open('/app/config/receiver/receiver_config.yml', 'r') as f:
    config = yaml.safe_load(f)



def log_event(event_type, event_data):
    client = KafkaClient(hosts=config['events']['hostname'] + ':' + str(config['events']['port']))
    topic = client.topics[str.encode(config['events']['topic'])]
    producer = topic.get_sync_producer()
    timestamp = int(time.time())  # Use UNIX timestamp
    trace_id = str(time.time_ns())  # Ensure it's a string
    if event_type == "race_events":
        event_entry = {
            "event_id": str(uuid.uuid4()),
            "car_number": event_data['car_number'],
            "lap_number": event_data['lap_number'],
            "event_type": event_data.get('event_type', None),
            "timestamp": timestamp,
            "trace_id": trace_id  
        }
    elif event_type == "telemetry_data":
        event_entry = {
            "telemetry_id": str(uuid.uuid4()),
            "car_number": event_data['car_number'],
            "lap_number": event_data['lap_number'],
            "speed": event_data.get('speed', None),
            "fuel_level": event_data.get('fuel_level', None),
            "rpm": event_data.get('rpm', None),
            "timestamp": timestamp,
            "trace_id": trace_id  
        }
    else:
        logger.error("Unknown event type: %s", event_type)
        return 400

    msg = {
        "type": event_type,
        "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": event_entry
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info("Produced event %s with a trace id of %s", event_type, trace_id)
    return 201

def submit_race_events(body):
    status_code = log_event("race_events", body)
    return NoContent, status_code

def submit_telemetry_data(body):
    status_code = log_event("telemetry_data", body)
    return NoContent, status_code

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api('./openapi.yml', base_path="/receiver", strict_validation=True, validate_responses=True)
if "CORS_ALLOW_ALL" in os.environ and os.environ["CORS_ALLOW_ALL"] == "yes":    
    app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )
if __name__ == '__main__':
    app.run(port=8080, host="0.0.0.0")
