import json
import logging
import time
import random
from pykafka import KafkaClient
from pykafka.common import OffsetType
from pykafka.exceptions import KafkaException

logger = logging.getLogger("basicLogger")

class KafkaProducerWrapper:
    def __init__(self, hostname, topic):
        self.hostname = hostname
        self.topic = topic
        self.client = None
        self.consumer = None
        self.producer = None
        self.connect()

    def connect(self):
        while True:
            logger.debug("Attempting to connect to Kafka...")
            if self.make_client():
                if self.make_consumer():
                    if self.make_producer():
                        logger.debug("Successfully connected to Kafka")
                        break

            time.sleep(random.randint(500, 1500) / 1000.0)

    def make_client(self):
        if self.client is not None:
            return True
        
        try:
            self.client = KafkaClient(hosts=self.hostname)
            logger.info("Kafka client created")
            return True
        except KafkaException as e:
            msg = f"Error creating Kafka client: {str(e)}"
            logger.error(msg)
            self.client = None
            self.consumer = None
            self.producer = None
            return False
        
    def make_consumer(self):
        if self.consumer is not None:
            return True
        
        if self.client is None:
            msg = "Kafka client is not initialized"
            logger.error(msg)
            return False
        
        try:
            topic = self.client.topics[str.encode(self.topic)]
            self.consumer = topic.get_simple_consumer(
                reset_offset_on_start=False,
                auto_offset_reset=OffsetType.LATEST
            )
            return True
        except KafkaException as e:
            msg = f"Error creating Kafka consumer: {str(e)}"
            logger.error(msg)
            self.consumer = None
            self.client = None
            self.producer = None
            return False
        
    def make_producer(self):
        if self.producer is not None:
            return True
        
        if self.client is None:
            msg = "Kafka client is not initialized"
            logger.error(msg)
            return False
        
        try:
            topic = self.client.topics[str.encode(self.topic)]
            self.producer = topic.get_sync_producer()
            return True
        except KafkaException as e:
            msg = f"Error creating Kafka producer: {str(e)}"
            logger.error(msg)
            self.consumer = None
            self.client = None
            self.producer = None
            return False
        
    def messages(self):
        if self.consumer is None:
            self.connect()

        while True:
            try:
                for msg in self.consumer:
                    yield msg
            except KafkaException as e:
                msg = f"Error consuming messages: {str(e)}"
                logger.error(msg)
                self.client = None
                self.consumer = None
                self.producer = None
                self.connect()