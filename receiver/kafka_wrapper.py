from pykafka import KafkaClient
import time
import os
import logging
import logging.config
import yaml

os.environ["LOG_FILENAME"] = "/app/logs/receiver.log"
with open('/app/config/log_config.yml', 'r') as f:
    log_config = yaml.safe_load(f)
logging.config.dictConfig(log_config)
logger = logging.getLogger("basicLogger")

with open('/app/config/receiver/receiver_config.yml', 'r') as f:
    config = yaml.safe_load(f)
    
    
class KafkaProducerWrapper:
    def __init__(self, hostname, topic):
        self.hostname = hostname
        self.topic_name = topic.encode()
        self.client = None
        self.producer = None
        self.connect()

    def connect(self):
        while True:
            try:
                logger.debug("Trying to connect to Kafka...")
                self.client = KafkaClient(hosts=self.hostname)
                topic = self.client.topics[self.topic_name]
                self.producer = topic.get_sync_producer()
                logger.info("Kafka producer connected!")
                break
            except Exception as e:
                logger.warning(f"Kafka producer connection failed: {e}")
                self.client = None
                self.producer = None
                time.sleep(1)

    def produce(self, msg):
        try:
            if not self.producer:
                self.connect()
            self.producer.produce(msg.encode('utf-8'))
        except Exception as e:
            logger.warning(f"Kafka produce failed: {e}")
            self.connect()
