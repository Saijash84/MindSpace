import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
from services.db_service import DatabaseService
from services.storage_service import StorageService

class HistoryViewer:
    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service

    def render_history_page(self, user_id: str):
        # Add storage status indicator
        if self.storage_service.is_firestore_available():
            st.sidebar.success("📊 Using Cloud Storage")
        else:
            st.sidebar.info("📊 Using Local Storage")
        
        st.title("📊 Your Mood History")

        # Time period filter
        time_period = st.selectbox(
            "Select Time Period",
            ["Last 7 Days", "Last 30 Days", "Last Year", "All Time"]
        )

        # Mood filter
        moods = ["All", "Happy", "Sad", "Angry", "Anxious", "Tired", "Calm"]
        mood_filter = st.multiselect("Filter by Mood", moods, default=["All"])

        # Get filtered data
        days = self._get_days_from_period(time_period)
        data = self.storage_service.get_user_history(
            user_id,
            days=days,
            mood_filter=None if "All" in mood_filter else mood_filter
        )

        if not data or not data.get('mood_history'):
            st.info("No mood data available for the selected period.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(data['mood_history'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Create visualization tabs
        tabs = st.tabs(["Mood Trends", "Activity Heatmap", "Statistics", "Raw Data"])

        with tabs[0]:
            self._render_mood_trends(df)

        with tabs[1]:
            self._render_activity_heatmap(df)

        with tabs[2]:
            self._render_statistics(df)

        with tabs[3]:
            self._render_raw_data(df)

    def _get_days_from_period(self, period: str) -> int:
        if period == "Last 7 Days":
            return 7
        elif period == "Last 30 Days":
            return 30
        elif period == "Last Year":
            return 365
        return None

    def _render_mood_trends(self, df: pd.DataFrame):
        st.subheader("Mood Trends Over Time")

        # Line chart of mood frequencies
        mood_counts = df.groupby([pd.Grouper(key='timestamp', freq='D'), 'mood']).size().unstack(fill_value=0)
        fig = px.line(mood_counts, title="Mood Trends")
        st.plotly_chart(fig, use_container_width=True)

        # Pie chart of overall mood distribution
        fig_pie = px.pie(df, names='mood', title="Overall Mood Distribution")
        st.plotly_chart(fig_pie, use_container_width=True)

    def _render_activity_heatmap(self, df: pd.DataFrame):
        st.subheader("Activity Heatmap")

        # Create daily activity counts
        daily_counts = df.groupby(df['timestamp'].dt.date).size().reset_index()
        daily_counts.columns = ['date', 'count']

        # Create calendar heatmap using Altair
        chart = alt.Chart(daily_counts).mark_rect().encode(
            x='date:O',
            y='count:Q',
            color='count:Q'
        ).properties(
            title="Daily Check-in Activity"
        )
        st.altair_chart(chart, use_container_width=True)

    def _render_statistics(self, df: pd.DataFrame):
        st.subheader("Mood Statistics")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Check-ins", len(df))

        with col2:
            most_common_mood = df['mood'].mode()[0]
            st.metric("Most Common Mood", most_common_mood)

        with col3:
            avg_daily_checkins = len(df) / (df['timestamp'].max() - df['timestamp'].min()).days
            st.metric("Avg. Daily Check-ins", f"{avg_daily_checkins:.1f}")

    def _render_raw_data(self, df: pd.DataFrame):
        st.subheader("Raw Data")

        # Add download button
        csv = df.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            "mood_history.csv",
            "text/csv",
            key='download-csv'
        )

        # Display paginated data
        page_size = 10
        page_number = st.number_input("Page", min_value=1, value=1)
        start_idx = (page_number - 1) * page_size
        end_idx = start_idx + page_size

        st.dataframe(df.iloc[start_idx:end_idx]) 