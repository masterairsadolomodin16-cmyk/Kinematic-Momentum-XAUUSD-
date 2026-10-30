"""Data models for XAUUSD tick telemetry and analytics."""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class TickData(BaseModel):
    """Standardized tick data schema."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str = "XAUUSD"
    bid: float
    ask: float
    volume: float
    trade_id: Optional[str] = None

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        return round(self.ask - self.bid, 3)

    @field_validator("timestamp", mode="before")
    def ensure_tz_aware(cls, v):
        if isinstance(v, str):
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class OrderBlockType(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class OrderBlock(BaseModel):
    id: str
    type: OrderBlockType
    top: float
    bottom: float
    start_time: datetime
    end_time: Optional[datetime] = None
    hit_count: int = 0
    decay_factor: float = 1.0


class FairValueGap(BaseModel):
    id: str
    is_bullish: bool
    top: float
    bottom: float
    timestamp: datetime
    filled: bool = False


class TelemetryMetrics(BaseModel):
    current_price: float
    velocity: float        # dP/dt ($/sec)
    acceleration: float    # d²P/dt² ($/sec²)
    momentum: float        # Velocity * normalized volume
    vwap_momentum: float   # Kinematic momentum weighted by VWAP deviation
    vwap_session: float
    vwap_rolling: float
    rsi: float
    highest_tick: float
    lowest_tick: float
    active_ob_overlap: Optional[str] = None
