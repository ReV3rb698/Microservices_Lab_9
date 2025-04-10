import connexion
from connexion import NoContent
from db_class import TelemetryData, RaceEvents
from datetime import datetime, timezone
import functools
from db import make_session
from sqlalchemy import select, func
import yaml
import logging
import logging.config
from dateutil import parser
from pykafka import KafkaClient
import json
from pykafka.common import OffsetType
from threading import Thread
import os
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
from kafka_wrapper import KafkaProducerWrapper

os.environ["LOG_FILENAME"] = "/app/logs/storage.log"

# Load logging configuration
with open('/app/config/log_config.yml', 'r') as f:
    log_config = yaml.safe_load(f)
logging.config.dictConfig(log_config)
logger = logging.getLogger("basicLogger")

with open('/app/config/storage/storage_config.yml', 'r') as f:
    config = yaml.safe_load(f)

kafka_producer = KafkaProducerWrapper(
    hostname=f"{config['events']['hostname']}:{config['events']['port']}",
    topic=config['events']['topic']
)

def process_messages():

    for msg in kafka_producer.messages:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info("Message: %s", msg)

        payload = msg['payload']
        if msg["type"] == "telemetry_data":
            submit_telemetry_data(payload)
        elif msg["type"] == "race_events":
            submit_race_events(payload)

def setup_kafka_thread():
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    
def use_db_session(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        session = make_session()
        try:
            result = func(session, *args, **kwargs)
            return result
        finally:
            session.close()
    return wrapper
# filepath: /c:/Users/xetro/OneDrive - BCIT/Term 4/Microservices/Week 6/storage/app.py
@use_db_session
def submit_race_events(session, body):
    event = RaceEvents(
        car_number=body['car_number'],
        lap_number=body['lap_number'],
        event_type=body['event_type'],
        timestamp=int(body['timestamp']),  
        trace_id=body['trace_id'] 
    )
    session.add(event)
    session.commit()
    
    logger.debug("Stored event %s with a trace id of %s", event.event_type, event.trace_id)
    return NoContent, 201

@use_db_session
def submit_telemetry_data(session, body):
    telemetry = TelemetryData(
        car_number=body['car_number'],
        lap_number=body['lap_number'],
        speed=body['speed'],
        fuel_level=body['fuel_level'],
        rpm=body['rpm'],
        timestamp=int(body['timestamp']), 
        trace_id=body['trace_id']
    )
    session.add(telemetry)
    session.commit()
   
    logger.debug("Stored event telemetry_data with a trace id of %s", telemetry.trace_id)
    return NoContent, 201
   

@use_db_session
def get_race_events(session, start_timestamp, end_timestamp):
    start_dt = int(start_timestamp) 
    end_dt = int(end_timestamp)  
    statement = select(RaceEvents).where(RaceEvents.timestamp >= start_dt).where(RaceEvents.timestamp < end_dt)
    results = [result.to_json() for result in session.execute(statement).scalars()]
    
    logger.info("Retrieved %d race events within the time range.", len(results))
    return results, 200

@use_db_session
def get_telemetry_data(session, start_timestamp, end_timestamp):
    start_dt = int(start_timestamp) 
    end_dt = int(end_timestamp) 
    statement = select(TelemetryData).where(TelemetryData.timestamp >= start_dt).where(TelemetryData.timestamp < end_dt)
    results = [result.to_json() for result in session.execute(statement).scalars()]
    
    logger.debug("Retrieved %d telemetry events within the time range.", len(results))
    return results, 200

@use_db_session
def get_record_count(session):
    """Get count of records in each table"""
    logger.info("GET request received for record count")
    
    # Count race events
    race_events_count = session.query(func.count(RaceEvents.event_id)).scalar()
    
    # Count telemetry data
    telemetry_data_count = session.query(func.count(TelemetryData.telemetry_id)).scalar()
    
    result = {
        "race_events": race_events_count,
        "telemetry_data": telemetry_data_count
    }
    
    logger.debug(f"Record count: {result}")
    logger.info("GET request for record count completed")
    
    return result, 200

@use_db_session
def get_event_ids(session):
    """Get list of race event IDs and trace IDs"""
    logger.info("GET request received for race event IDs")
    
    statement = select(RaceEvents.event_id, RaceEvents.trace_id)
    results = [{"event_id": result[0], "trace_id": result[1]} for result in session.execute(statement)]
    
    logger.debug(f"Retrieved {len(results)} race event IDs")
    logger.info("GET request for race event IDs completed")
    
    return results, 200

@use_db_session
def get_telemetry_ids(session):
    """Get list of telemetry IDs and trace IDs"""
    logger.info("GET request received for telemetry IDs")
    
    statement = select(TelemetryData.telemetry_id, TelemetryData.trace_id)
    results = [{"telemetry_id": result[0], "trace_id": result[1]} for result in session.execute(statement)]
    
    logger.debug(f"Retrieved {len(results)} telemetry IDs")
    logger.info("GET request for telemetry IDs completed")
    
    return results, 200

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api('./openapi.yml', base_path="/storage", strict_validation=True, validate_responses=True)
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
    setup_kafka_thread()
    app.run(port=8090, host="0.0.0.0")
