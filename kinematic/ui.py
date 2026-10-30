"""UI helpers for displaying telemetry strips and alerts."""

import streamlit as st
from kinematic.models import TelemetryMetrics


def render_telemetry_strip(m: TelemetryMetrics):
    """Renders the top HUD strip displaying kinematic metrics."""
    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Current Price", f"${m.current_price:.2f}")
    
    vel_color = "normal" if abs(m.velocity) < 0.1 else ("inverse" if m.velocity < 0 else "normal")
    col2.metric("Velocity (dP/dt)", f"{m.velocity:+.3f} $/s", delta=f"{m.velocity:.3f}")
    
    col3.metric("Acceleration", f"{m.acceleration:+.4f} $/s²")
    col4.metric("Kinematic Momentum", f"{m.momentum:+.2f}")
    col5.metric("RSI (14)", f"{m.rsi:.1f}")
