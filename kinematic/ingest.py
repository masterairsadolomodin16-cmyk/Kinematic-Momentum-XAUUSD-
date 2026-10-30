"""Async tick ingestion streams supporting APISED Real-Time Polling & Simulation."""

import asyncio
import logging
import math
import random
import aiohttp
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from kinematic.models import TickData

logger = logging.getLogger(__name__)


class APISEDLiveConnector:
    """Real-time live client connector for APISED Market Data API."""

    def __init__(self, api_key: str, symbol: str = "XAU", poll_interval: float = 1.0):
        self.api_key = api_key
        self.symbol = symbol
        self.poll_interval = poll_interval
        # APISED Market Data Endpoint
        self.url = f"https://apised.com/v1/market-data?symbols={self.symbol}&base_currency=USD"

    async def connect_and_stream(self) -> AsyncGenerator[TickData, None]:
        """Polls APISED real-time market data endpoint and yields standardized ticks."""
        headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            count = 0
            while True:
                try:
                    async with session.get(self.url, headers=headers, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Parse APISED market data structure
                            rates = data.get("rates", {}) or data.get("data", {})
                            item = rates.get(self.symbol, {})
                            
                            current_price = item.get("current") or item.get("price") or item.get("value")
                            
                            if current_price is not None:
                                price_val = float(current_price)
                                # Calculate estimated spread if bid/ask are missing
                                bid = round(item.get("bid", price_val - 0.15), 2)
                                ask = round(item.get("ask", price_val + 0.15), 2)
                                vol = float(item.get("volume", 10.0))

                                count += 1
                                yield TickData(
                                    timestamp=datetime.now(timezone.utc),
                                    symbol="XAUUSD",
                                    bid=bid,
                                    ask=ask,
                                    volume=vol,
                                    trade_id=f"APISED-{count}"
                                )
                        else:
                            logger.error(f"APISED returned status code: {response.status}")

                except Exception as e:
                    logger.error(f"APISED connection error: {e}")

                await asyncio.sleep(self.poll_interval)


class SimulatedTickGenerator:
    """High-fidelity brownian bridge simulator initialized at real-world baseline (~$4000)."""

    def __init__(self, initial_price: float = 3994.00, tick_rate_hz: float = 10.0):
        self.price = initial_price
        self.tick_rate_hz = tick_rate_hz
        self.spread = 0.25
        self.dt = 1.0 / tick_rate_hz
        self.count = 0

    async def stream(self) -> AsyncGenerator[TickData, None]:
        while True:
            self.count += 1
            drift = 0.02 * math.sin(self.count / 10.0)
            volatility = random.gauss(0, 0.12)
            if random.random() < 0.05:
                volatility *= 3.5

            self.price += drift + volatility
            bid = round(self.price, 2)
            ask = round(bid + self.spread, 2)
            volume = round(abs(random.gauss(15.0, 5.0)), 2)

            yield TickData(
                timestamp=datetime.now(timezone.utc),
                symbol="XAUUSD",
                bid=bid,
                ask=ask,
                volume=volume,
                trade_id=f"SIM-{self.count}"
            )
            await asyncio.sleep(self.dt)
