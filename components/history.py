import streamlit as st
from datetime import datetime
import pandas as pd

class UserHistory:
    def __init__(self):
        # Initialize session state for history if not exists
        if 'user_history' not in st.session_state:
            st.session_state.user_history = {
                'mood_checkins': [],
                'tasks': [],
                'stories': [],
                'sessions': []
            }

    def add_mood_checkin(self, mood, timestamp=None):
        """Add a mood check-in to history"""
        if timestamp is None:
            timestamp = datetime.now()
        st.session_state.user_history['mood_checkins'].append({
            'mood': mood,
            'timestamp': timestamp.isoformat()
        })

    def add_task(self, task_name, status, timestamp=None):
        """Add a task completion to history"""
        if timestamp is None:
            timestamp = datetime.now()
        st.session_state.user_history['tasks'].append({
            'task_name': task_name,
            'status': status,
            'timestamp': timestamp.isoformat()
        })

    def add_story(self, theme, timestamp=None):
        """Add a story generation to history"""
        if timestamp is None:
            timestamp = datetime.now()
        st.session_state.user_history['stories'].append({
            'theme': theme,
            'timestamp': timestamp.isoformat()
        })

    def add_session(self, action, timestamp=None):
        """Add a login/logout to history"""
        if timestamp is None:
            timestamp = datetime.now()
        st.session_state.user_history['sessions'].append({
            'action': action,
            'timestamp': timestamp.isoformat()
        })

    def get_mood_history(self):
        """Get mood check-in history as DataFrame"""
        if not st.session_state.user_history['mood_checkins']:
            return None
        df = pd.DataFrame(st.session_state.user_history['mood_checkins'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df.sort_values('timestamp', ascending=False)

    def get_task_history(self):
        """Get task history as DataFrame"""
        if not st.session_state.user_history['tasks']:
            return None
        df = pd.DataFrame(st.session_state.user_history['tasks'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df.sort_values('timestamp', ascending=False)

    def get_story_history(self):
        """Get story generation history as DataFrame"""
        if not st.session_state.user_history['stories']:
            return None
        df = pd.DataFrame(st.session_state.user_history['stories'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df.sort_values('timestamp', ascending=False)

    def get_session_history(self):
        """Get session history as DataFrame"""
        if not st.session_state.user_history['sessions']:
            return None
        df = pd.DataFrame(st.session_state.user_history['sessions'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df.sort_values('timestamp', ascending=False)

    def render_history(self):
        """Render the history dashboard"""
        st.title("📊 Your Activity History")
        
        # Create tabs for different types of history
        tab1, tab2, tab3, tab4 = st.tabs([
            "Mood Check-ins", "Tasks", "Stories", "Sessions"
        ])
        
        with tab1:
            st.subheader("Mood Check-in History")
            mood_df = self.get_mood_history()
            if mood_df is not None:
                # Display mood trend
                st.line_chart(mood_df.set_index('timestamp')['mood'])
                # Display detailed history
                st.dataframe(
                    mood_df,
                    column_config={
                        "timestamp": st.column_config.DatetimeColumn(
                            "Time",
                            format="D MMM YYYY, h:mm a"
                        ),
                        "mood": "Mood"
                    },
                    hide_index=True
                )
            else:
                st.info("No mood check-ins recorded yet.")
        
        with tab2:
            st.subheader("Task History")
            task_df = self.get_task_history()
            if task_df is not None:
                # Task completion statistics
                col1, col2 = st.columns(2)
                with col1:
                    total_tasks = len(task_df)
                    completed_tasks = len(task_df[task_df['status'] == 'completed'])
                    st.metric("Total Tasks", total_tasks)
                with col2:
                    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                    st.metric("Completion Rate", f"{completion_rate:.1f}%")
                
                # Display task history
                st.dataframe(
                    task_df,
                    column_config={
                        "timestamp": st.column_config.DatetimeColumn(
                            "Time",
                            format="D MMM YYYY, h:mm a"
                        ),
                        "task_name": "Task",
                        "status": "Status"
                    },
                    hide_index=True
                )
            else:
                st.info("No tasks recorded yet.")
        
        with tab3:
            st.subheader("Story Generation History")
            story_df = self.get_story_history()
            if story_df is not None:
                # Story theme distribution
                st.bar_chart(story_df['theme'].value_counts())
                
                # Display story history
                st.dataframe(
                    story_df,
                    column_config={
                        "timestamp": st.column_config.DatetimeColumn(
                            "Time",
                            format="D MMM YYYY, h:mm a"
                        ),
                        "theme": "Theme"
                    },
                    hide_index=True
                )
            else:
                st.info("No stories generated yet.")
        
        with tab4:
            st.subheader("Session History")
            session_df = self.get_session_history()
            if session_df is not None:
                # Display session history
                st.dataframe(
                    session_df,
                    column_config={
                        "timestamp": st.column_config.DatetimeColumn(
                            "Time",
                            format="D MMM YYYY, h:mm a"
                        ),
                        "action": "Action"
                    },
                    hide_index=True
                )
            else:
                st.info("No session history recorded yet.")

def render_history():
    history = UserHistory()
    history.render_history() 