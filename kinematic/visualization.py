"""Plotly graphics engine for Kinematic Telemetry rendering."""

from typing import List
import pandas as pd
import plotly.graph_objects as gg
from plotly.subplots import make_subplots

from kinematic.models import OrderBlock, FairValueGap


def build_telemetry_chart(
    df: pd.DataFrame,
    order_blocks: List[OrderBlock],
    fvgs: List[FairValueGap],
    session_vwap: pd.Series,
    rolling_vwap: pd.Series
) -> gg.Figure:
    """Builds multi-panel dark theme chart with price, VWAP, FVG polygons, and order blocks."""

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
        subplot_titles=("XAUUSD Kinematic Price Telemetry", "Tick Volume Density")
    )

    if df.empty:
        return fig

    # 1. Bid / Ask Price Ticks
    fig.add_trace(
        gg.Scatter(
            x=df['timestamp'], y=df['bid'],
            mode='lines', name='Bid',
            line=dict(color='#00F0FF', width=1.5)
        ), row=1, col=1
    )
    fig.add_trace(
        gg.Scatter(
            x=df['timestamp'], y=df['ask'],
            mode='lines', name='Ask',
            line=dict(color='#FF0055', width=1.0, dash='dot')
        ), row=1, col=1
    )

    # 2. Session VWAP
    fig.add_trace(
        gg.Scatter(
            x=df['timestamp'], y=session_vwap,
            mode='lines', name='Session VWAP',
            line=dict(color='#FFB800', width=2)
        ), row=1, col=1
    )

    # 3. Order Blocks Overlay Shapes
    for ob in order_blocks:
        color = "rgba(0, 255, 128, 0.25)" if ob.type.value == "BULLISH" else "rgba(255, 0, 64, 0.25)"
        border = "#00FF80" if ob.type.value == "BULLISH" else "#FF0040"
        fig.add_shape(
            type="rect",
            x0=ob.start_time, x1=df['timestamp'].iloc[-1],
            y0=ob.bottom, y1=ob.top,
            fillcolor=color,
            line=dict(color=border, width=1, dash="dash"),
            row=1, col=1
        )

    # 4. Fair Value Gaps (FVG) Polygons
    for fvg in fvgs:
        fvg_color = "rgba(0, 240, 255, 0.2)" if fvg.is_bullish else "rgba(255, 184, 0, 0.2)"
        fig.add_shape(
            type="rect",
            x0=fvg.timestamp, x1=df['timestamp'].iloc[-1],
            y0=fvg.bottom, y1=fvg.top,
            fillcolor=fvg_color,
            line=dict(width=0),
            row=1, col=1
        )

    # 5. Volume Subplot
    fig.add_trace(
        gg.Bar(
            x=df['timestamp'], y=df['volume'],
            name='Volume',
            marker_color='#7000FF'
        ), row=2, col=1
    )

    # Formatting / Theme
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0A0E17",
        plot_bgcolor="#0A0E17",
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False,
        height=620
    )
    
    fig.update_xaxes(gridcolor="#1F293D")
    fig.update_yaxes(gridcolor="#1F293D")

    return fig
