"""Async tick ingestion streams with High-Fidelity Simulator & Production Websocket Template."""

import asyncio
import json
import random
import time
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional
import websockets

from kinematic.models import TickData


class SimulatedTickGenerator:
    """High-fidelity brownian bridge simulator for XAUUSD price action."""

    def __init__(self, initial_price: float = 2650.00, tick_rate_hz: float = 20.0):
        self.price = initial_price
        self.tick_rate_hz = tick_rate_hz
        self.spread = 0.25  # Typical XAUUSD spread
        self.dt = 1.0 / tick_rate_hz
        self.count = 0

    async def stream(self) -> AsyncGenerator[TickData, None]:
        while True:
            self.count += 1
            # Random walk with mean-reverting momentum pulse
            drift = 0.02 * math.sin(self.count / 10.0)
            volatility = random.gauss(0, 0.12)
            
            # Occasional momentum spike
            if random.random() < 0.05:
                volatility *= 3.5

            self.price += drift + volatility
            bid = round(self.price, 2)
            ask = round(bid + self.spread, 2)
            volume = round(abs(random.gauss(15.0, 5.0)), 2)

            tick = TickData(
                timestamp=datetime.now(timezone.utc),
                symbol="XAUUSD",
                bid=bid,
                ask=ask,
                volume=volume,
                trade_id=f"SIM-{self.count}"
            )
            yield tick
            await asyncio.sleep(self.dt)


import math


class ProductionWebsocketConnector:
    """Production WebSocket client template for live broker data (OANDA, FXCM, Alpaca)."""

    def __init__(self, uri: str, api_key: Optional[str] = None):
        self.uri = uri
        self.api_key = api_key

    async def connect_and_stream(self) -> AsyncGenerator[TickData, None]:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with websockets.connect(self.uri, extra_headers=headers) as ws:
            # Subscribe payload example
            sub_msg = {"action": "subscribe", "params": {"symbol": "XAUUSD"}}
            await ws.send(json.dumps(sub_msg))

            async for message in ws:
                data = json.loads(message)
                # Standardize incoming payload to TickData model
                if "bid" in data and "ask" in data:
                    yield TickData(
                        timestamp=datetime.now(timezone.utc),
                        symbol="XAUUSD",
                        bid=float(data["bid"]),
                        ask=float(data["ask"]),
                        volume=float(data.get("volume", 1.0)),
                        trade_id=str(data.get("id", ""))
                    )
