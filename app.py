"""Streamlit Main Entry Point — Kinematic Momentum XAUUSD Telemetry."""

import asyncio
import time
import pandas as pd
import streamlit as st

from kinematic.indicators import IndicatorSuite, KinematicEngine
from kinematic.ingest import SimulatedTickGenerator
from kinematic.models import TelemetryMetrics
from kinematic.ui import render_telemetry_strip
from kinematic.utils import RingBuffer
from kinematic.visualization import build_telemetry_chart

# Page Config
st.set_page_config(
    page_title="Kinematic Momentum — XAUUSD Telemetry",
    page_icon="⚡",
    layout="wide"
)

# Initialize Session State
if "ring_buffer" not in st.session_state:
    st.session_state.ring_buffer = RingBuffer(capacity=500)
if "running" not in st.session_state:
    st.session_state.running = True

# Sidebar Controls
st.sidebar.title("⚡ Control Center")
mode = st.sidebar.radio("Data Stream Mode", ["Simulator Mode", "Live Broker Feed (WebSocket)"])
tick_rate = st.sidebar.slider("Tick Refresh Rate (Hz)", min_value=1, max_value=50, value=10)

st.sidebar.subheader("Kinematic Parameters")
window_sec = st.sidebar.slider("Velocity Window (sec)", 1.0, 10.0, 3.0)
rsi_period = st.sidebar.number_input("RSI Period", min_value=5, max_value=50, value=14)

st.sidebar.subheader("Presets")
if st.sidebar.button("Scalper Preset"):
    window_sec = 1.5
    rsi_period = 9

# Main Layout
st.title("Kinematic Momentum — XAUUSD Tick Telemetry")

hud_placeholder = st.empty()
chart_placeholder = st.empty()

# Streaming loop
async def main_loop():
    generator = SimulatedTickGenerator(tick_rate_hz=tick_rate)
    kin_engine = KinematicEngine(window_seconds=window_sec)

    async for tick in generator.stream():
        st.session_state.ring_buffer.append(tick)
        ticks = st.session_state.ring_buffer.get_all()
        
        if len(ticks) < 5:
            continue

        # Prepare DataFrame
        df = pd.DataFrame([t.model_dump() for t in ticks])
        df['mid'] = (df['bid'] + df['ask']) / 2.0

        # Calculations
        vel, accel, mom, norm_vol = kin_engine.compute(ticks)
        rsi = IndicatorSuite.compute_rsi(df['mid'].values, period=rsi_period)
        s_vwap, r_vwap = IndicatorSuite.compute_vwap(df)
        order_blocks = IndicatorSuite.detect_order_blocks(df)
        fvgs = IndicatorSuite.detect_fvg(df)

        metrics = TelemetryMetrics(
            current_price=ticks[-1].mid,
            velocity=vel,
            acceleration=accel,
            momentum=mom,
            vwap_momentum=mom * (ticks[-1].mid - s_vwap.iloc[-1]),
            vwap_session=s_vwap.iloc[-1],
            vwap_rolling=r_vwap.iloc[-1],
            rsi=rsi,
            highest_tick=float(df['mid'].max()),
            lowest_tick=float(df['mid'].min())
        )

        # Render HUD & Charts
        with hud_placeholder.container():
            render_telemetry_strip(metrics)

        fig = build_telemetry_chart(df, order_blocks, fvgs, s_vwap, r_vwap)
        chart_placeholder.plotly_chart(fig, use_container_width=True, key=f"plotly_chart_{time.time()}")

        await asyncio.sleep(1.0 / tick_rate)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except Exception as e:
        st.warning("Stream re-initializing...")
