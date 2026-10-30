"""High-performance indicators for kinematic momentum and SMC structures."""

from collections import deque
from datetime import datetime
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd

from kinematic.models import TickData, OrderBlock, OrderBlockType, FairValueGap, TelemetryMetrics


class KinematicEngine:
    """Calculates kinematic derivatives (Velocity, Acceleration, Kinematic Momentum)."""
    
    def __init__(self, window_seconds: float = 5.0, volume_window: int = 50):
        self.window_seconds = window_seconds
        self.volume_window = volume_window

    def compute(self, ticks: List[TickData]) -> Tuple[float, float, float, float]:
        if len(ticks) < 3:
            return 0.0, 0.0, 0.0, 0.0

        now = ticks[-1].timestamp.timestamp()
        cutoff = now - self.window_seconds
        
        # Filter recent ticks in window
        recent_ticks = [t for t in ticks if t.timestamp.timestamp() >= cutoff]
        if len(recent_ticks) < 2:
            recent_ticks = ticks[-3:]

        t_coords = np.array([t.timestamp.timestamp() for t in recent_ticks])
        p_coords = np.array([t.mid for t in recent_ticks])
        v_coords = np.array([t.volume for t in recent_ticks])

        dt = t_coords[-1] - t_coords[0]
        if dt <= 1e-6:
            return 0.0, 0.0, 0.0, 0.0

        # Velocity (dP/dt) via linear regression slope over the window
        velocity = float(np.polyfit(t_coords - t_coords[0], p_coords, 1)[0])

        # Velocity array for acceleration calculation
        vels = []
        for i in range(1, len(t_coords)):
            dt_i = t_coords[i] - t_coords[i-1]
            if dt_i > 1e-6:
                vels.append((p_coords[i] - p_coords[i-1]) / dt_i)
            else:
                vels.append(0.0)

        # Acceleration (d²P/dt²)
        acceleration = float(np.mean(np.diff(vels))) if len(vels) > 1 else 0.0

        # Volume normalization
        all_vols = [t.volume for t in ticks[-self.volume_window:]]
        avg_vol = float(np.mean(all_vols)) if all_vols else 1.0
        curr_vol = v_coords[-1]
        norm_vol = curr_vol / (avg_vol + 1e-6)

        # Kinematic Momentum
        momentum = velocity * norm_vol

        return velocity, acceleration, momentum, norm_vol


class IndicatorSuite:
    """Consolidated quantitative and Smart Money Concepts (SMC) engine."""

    @staticmethod
    def compute_rsi(prices: np.ndarray, period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100.0 - (100.0 / (1.0 + rs)))

    @staticmethod
    def compute_vwap(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
        """Calculates Session VWAP and Rolling VWAP."""
        if df.empty or 'mid' not in df.columns or 'volume' not in df.columns:
            return pd.Series(dtype=float), pd.Series(dtype=float)

        typical_price = df['mid']
        cum_tp_vol = (typical_price * df['volume']).cumsum()
        cum_vol = df['volume'].cumsum()
        session_vwap = cum_tp_vol / np.where(cum_vol == 0, 1e-6, cum_vol)

        # Rolling VWAP (last 100 ticks)
        rolling_tp_vol = (typical_price * df['volume']).rolling(100, min_periods=1).sum()
        rolling_vol = df['volume'].rolling(100, min_periods=1).sum()
        rolling_vwap = rolling_tp_vol / np.where(rolling_vol == 0, 1e-6, rolling_vol)

        return session_vwap, rolling_vwap

    @staticmethod
    def detect_order_blocks(df: pd.DataFrame, min_candles: int = 3, range_mult: float = 1.2) -> List[OrderBlock]:
        """Heuristic identification of Smart Money Order Blocks."""
        if len(df) < min_candles + 2:
            return []

        obs = []
        # Aggregate ticks into 5-tick mini-bars for consolidation analysis
        bars = df.iloc[::5].copy()
        if len(bars) < min_candles + 1:
            return []

        ranges = (bars['ask'] - bars['bid']).values
        avg_range = np.mean(ranges)

        for i in range(len(bars) - min_candles):
            sub = bars.iloc[i : i + min_candles]
            p_start = sub['mid'].iloc[0]
            p_end = sub['mid'].iloc[-1]
            sub_range = sub['mid'].max() - sub['mid'].min()

            # Consolidation heuristic
            if sub_range <= avg_range * range_mult:
                # Impulse check on next bar
                next_p = bars['mid'].iloc[i + min_candles]
                if next_p > p_end + (avg_range * 1.5):
                    obs.append(OrderBlock(
                        id=f"OB_BULL_{i}",
                        type=OrderBlockType.BULLISH,
                        top=float(sub['mid'].max()),
                        bottom=float(sub['mid'].min()),
                        start_time=sub['timestamp'].iloc[0]
                    ))
                elif next_p < p_end - (avg_range * 1.5):
                    obs.append(OrderBlock(
                        id=f"OB_BEAR_{i}",
                        type=OrderBlockType.BEARISH,
                        top=float(sub['mid'].max()),
                        bottom=float(sub['mid'].min()),
                        start_time=sub['timestamp'].iloc[0]
                    ))
        return obs[-6:]  # Return most recent 6 zones

    @staticmethod
    def detect_fvg(df: pd.DataFrame) -> List[FairValueGap]:
        """Detect Fair Value Gaps across mini bars."""
        if len(df) < 15:
            return []

        fvgs = []
        # Sample mini-bars
        bars = df.iloc[::3].copy().reset_index(drop=True)
        for i in range(2, len(bars)):
            c1_high = bars.loc[i-2, 'ask']
            c1_low = bars.loc[i-2, 'bid']
            c3_high = bars.loc[i, 'ask']
            c3_low = bars.loc[i, 'bid']

            # Bullish FVG: Candle 3 Low > Candle 1 High
            if c3_low > c1_high:
                fvgs.append(FairValueGap(
                    id=f"FVG_BULL_{i}",
                    is_bullish=True,
                    top=float(c3_low),
                    bottom=float(c1_high),
                    timestamp=bars.loc[i, 'timestamp']
                ))
            # Bearish FVG: Candle 3 High < Candle 1 Low
            elif c3_high < c1_low:
                fvgs.append(FairValueGap(
                    id=f"FVG_BEAR_{i}",
                    is_bullish=False,
                    top=float(c1_low),
                    bottom=float(c3_high),
                    timestamp=bars.loc[i, 'timestamp']
                ))
        return fvgs[-4:]
