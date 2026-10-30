"""Streamlit Main Entry Point — Kinematic Momentum Real-Time Telemetry."""

import asyncio
import os
import time
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from kinematic.indicators import IndicatorSuite, KinematicEngine
from kinematic.ingest import SimulatedTickGenerator, APISEDLiveConnector
from kinematic.models import TelemetryMetrics
from kinematic.ui import render_telemetry_strip
from kinematic.utils import RingBuffer
from kinematic.visualization import build_telemetry_chart

load_dotenv()

st.set_page_config(
    page_title="Kinematic Momentum — XAUUSD Telemetry",
    page_icon="⚡",
    layout="wide"
)

# Custom CSS presentation interface
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

if "ring_buffer" not in st.session_state:
    st.session_state.ring_buffer = RingBuffer(capacity=500)

# Sidebar Controls
st.sidebar.title("⚡ Control Center")
mode = st.sidebar.radio("Data Stream Mode", ["Live APISED Feed (Real-Time)", "Simulator Mode"])
tick_rate = st.sidebar.slider("Refresh Rate (Hz / Interval)", min_value=1, max_value=20, value=5)

st.sidebar.subheader("Kinematic Parameters")
window_sec = st.sidebar.slider("Velocity Window (sec)", 1.0, 10.0, 3.0)
rsi_period = st.sidebar.number_input("RSI Period", min_value=5, max_value=50, value=14)

st.title("Kinematic Momentum — XAUUSD Real-Time Telemetry")

hud_placeholder = st.empty()
chart_placeholder = st.empty()


async def main_loop():
    if mode == "Live APISED Feed (Real-Time)":
        api_key = os.getenv("APISED_API_KEY", "sk_Ef1FB50ec771Daf256E81B3d6Ede72c8857C123649454744")
        connector = APISEDLiveConnector(api_key=api_key, symbol="XAU", poll_interval=1.0 / tick_rate)
        stream_generator = connector.connect_and_stream()
    else:
        stream_generator = SimulatedTickGenerator(initial_price=3994.00, tick_rate_hz=tick_rate).stream()

    kin_engine = KinematicEngine(window_seconds=window_sec)

    async for tick in stream_generator:
        st.session_state.ring_buffer.append(tick)
        ticks = st.session_state.ring_buffer.get_all()

        if len(ticks) < 3:
            continue

        df = pd.DataFrame([t.model_dump() for t in ticks])
        df['mid'] = (df['bid'] + df['ask']) / 2.0

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

        with hud_placeholder.container():
            render_telemetry_strip(metrics)

        fig = build_telemetry_chart(df, order_blocks, fvgs, s_vwap, r_vwap)
        chart_placeholder.plotly_chart(fig, use_container_width=True, key=f"plotly_chart_{time.time()}")

        if mode == "Simulator Mode":
            await asyncio.sleep(1.0 / tick_rate)


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except Exception as e:
        st.warning(f"Re-connecting stream... ({e})")
        time.sleep(1)
        st.rerun()
