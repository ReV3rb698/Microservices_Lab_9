import connexion
from connexion import NoContent
import json
import logging
import logging.config
import yaml
from pykafka import KafkaClient
import os

os.environ["LOG_FILENAME"] = "/app/logs/analyzer.log"

# Load logging configuration
with open("/app/config/log_config.yml", "r") as f:
    log_config = yaml.safe_load(f)
logging.config.dictConfig(log_config)
logger = logging.getLogger("basicLogger")

# Load application configuration
with open("/app/config/analyzer/analyzer_config.yml", "r") as f:
    app_config = yaml.safe_load(f)

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
    
app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api("./openapi.yml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8100, host="0.0.0.0")