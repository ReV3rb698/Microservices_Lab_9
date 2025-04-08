from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import Integer, String, DateTime, func
import time

class Base(DeclarativeBase):
    pass

class RaceEvents(Base):
    __tablename__ = "race_events"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id = mapped_column(String(50), nullable=False)
    car_number = mapped_column(Integer, nullable=False)
    lap_number = mapped_column(String(50), nullable=False)
    event_type = mapped_column(String(50), nullable=False)
    timestamp = mapped_column(Integer, nullable=False)  # Change to Integer
    trace_id = mapped_column(String(50), nullable=False)
    date_created = mapped_column(Integer, nullable=False, default=lambda: int(time.time()))  # Change to Integer

    def to_json(self):
        return {
            "event_id": self.event_id,
            "car_number": self.car_number,
            "lap_number": self.lap_number,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "date_created": self.date_created
        }
        
class TelemetryData(Base):
    __tablename__ = "telemetry_data"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    telemetry_id = mapped_column(String(50), nullable=False)
    car_number = mapped_column(Integer, nullable=False)
    lap_number = mapped_column(Integer, nullable=False)
    speed = mapped_column(Integer, nullable=False)
    fuel_level = mapped_column(Integer, nullable=False)
    rpm = mapped_column(Integer, nullable=False)
    timestamp = mapped_column(Integer, nullable=False)  # Change to Integer
    trace_id = mapped_column(String(50), nullable=False)
    date_created = mapped_column(Integer, nullable=False, default=lambda: int(time.time()))  # Change to Integer

    def to_json(self):
        return {
            "telemetry_id": self.telemetry_id,
            "car_number": self.car_number,
            "lap_number": self.lap_number,
            "speed": self.speed,
            "fuel_level": self.fuel_level,
            "rpm": self.rpm,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "date_created": self.date_created
        }