import connexion
from connexion import NoContent
from apscheduler.schedulers.background import BackgroundScheduler
import json
import os
import logging
import logging.config
import yaml
from datetime import datetime, timezone
import httpx
import time
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

os.environ["LOG_FILENAME"] = "/app/logs/processing.log"

# Load logging configuration
with open("/app/config/log_config.yml", "r") as f:
    log_config = yaml.safe_load(f)
logging.config.dictConfig(log_config)
logger = logging.getLogger("basicLogger")

# Load application configuration
with open("/app/config/processing/processing_config.yml", "r") as f:
    app_config = yaml.safe_load(f)

# Get values from configuration
STATISTICS_FILE = app_config["datastore"]["filename"]
PROCESSING_INTERVAL = app_config["scheduler"]["interval"]
RACE_EVENTS_URL = app_config["eventstores"]["race_events"]["url"]
TELEMETRY_DATA_URL = app_config["eventstores"]["telemetry_data"]["url"]

def get_statistics():
    logger.info("GET request received for statistics")

    if os.path.exists(STATISTICS_FILE):
        with open(STATISTICS_FILE, "r") as f:
            stats = json.load(f)
        
        logger.debug(f"Statistics content: {json.dumps(stats, indent=2)}")
        logger.info("GET request for statistics completed")
        return stats, 200
    
    logger.error("Statistics file does not exist")
    return {"message": "Statistics do not exist"}, 404

def populate_stats():
    logger.info("Periodic processing started")

    if os.path.exists(STATISTICS_FILE):
        with open(STATISTICS_FILE, "r") as f:
            stats = json.load(f)
    else:
        stats = {
            "stat_type_counts": {},
            "max_speed": None,
            "min_speed": None,
            "avg_speed": None,
            "last_processed_timestamp": int(time.time())
        }

    if "stat_type_counts" not in stats:
        stats["stat_type_counts"] = {}

    end_timestamp = int(time.time())
    start_timestamp = stats.get("last_processed_timestamp", int(time.time()))

    logger.info(f"Fetching race events from {start_timestamp} to {end_timestamp}")
    race_response = httpx.get(f"{RACE_EVENTS_URL}?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}")
    logger.info(f"Fetching telemetry data from {start_timestamp} to {end_timestamp}")
    telemetry_response = httpx.get(f"{TELEMETRY_DATA_URL}?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}")

    if race_response.status_code != 200:
        logger.error(f"Failed to retrieve race events: {race_response.status_code}")
        return

    if telemetry_response.status_code != 200:
        logger.error(f"Failed to retrieve telemetry data: {telemetry_response.status_code}")
        return

    new_race_events = race_response.json()
    new_telemetry_data = telemetry_response.json()

    logger.info(f"Retrieved {len(new_race_events)} new race events")
    logger.info(f"Retrieved {len(new_telemetry_data)} new telemetry data entries")

    stat_counts = stats["stat_type_counts"]
    speeds = []

    for event in new_race_events:
        stat_counts["race_events"] = stat_counts.get("race_events", 0) + 1
    stat_counts["telemetry"] = stat_counts.get("telemetry", 0) + len(new_telemetry_data)
    
    for telemetry in new_telemetry_data:
        if "speed" in telemetry:
            speeds.append(telemetry["speed"])

    if speeds:
        stats["max_speed"] = max(speeds)
        stats["min_speed"] = min(speeds)
        stats["avg_speed"] = sum(speeds) / len(speeds)

    stats["last_processed_timestamp"] = end_timestamp

    stats_to_save = {
        "stat_type_counts": stats["stat_type_counts"],
        "max_speed": stats["max_speed"],
        "min_speed": stats["min_speed"],
        "avg_speed": stats["avg_speed"],
        "last_processed_timestamp": stats["last_processed_timestamp"]
    }

    with open(STATISTICS_FILE, "w") as f:
        json.dump(stats_to_save, f, indent=2)

    logger.info(f"Processed {len(new_race_events)} race events and {len(new_telemetry_data)} telemetry entries.")
    logger.debug(f"Updated statistics: {json.dumps(stats_to_save, indent=2)}")
    logger.info("Periodic processing ended")
    
def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval', seconds=PROCESSING_INTERVAL)
    sched.start()

app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api("./openapi.yml", base_path="/processing", strict_validation=True, validate_responses=True)
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
    app.run(port=8091, host="0.0.0.0")
