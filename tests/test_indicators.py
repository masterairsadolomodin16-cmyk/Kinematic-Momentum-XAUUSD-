import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta

from kinematic.models import TickData
from kinematic.indicators import KinematicEngine, IndicatorSuite


def test_rsi_calculation():
    prices = np.array([10, 12, 11, 13, 15, 14, 16, 18, 17, 19, 21, 20, 22, 24, 23, 25], dtype=float)
    rsi = IndicatorSuite.compute_rsi(prices, period=14)
    assert 0 <= rsi <= 100
    assert rsi > 50  # Upward trending series should be > 50


def test_kinematic_engine():
    now = datetime.now(timezone.utc)
    ticks = [
        TickData(timestamp=now - timedelta(seconds=2), bid=2650.0, ask=2650.2, volume=10),
        TickData(timestamp=now - timedelta(seconds=1), bid=2651.0, ask=2651.2, volume=12),
        TickData(timestamp=now, bid=2652.0, ask=2652.2, volume=15)
    ]
    
    engine = KinematicEngine(window_seconds=3.0)
    velocity, accel, mom, norm_vol = engine.compute(ticks)
    
    assert velocity > 0  # Price moved from 2650 to 2652
    assert isinstance(mom, float)
