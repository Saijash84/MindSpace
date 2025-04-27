import streamlit as st
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from config import db, is_firestore_available
from services.storage_service import StorageService

def get_user_history(db, user_id):
    """Fetch user history from Firestore"""
    if not is_firestore_available():
        st.warning("Database not available. Using local storage.")
        return {
            'mood_history': st.session_state.get('local_mood_history', []),
            'focus_history': st.session_state.get('local_focus_history', []),
            'task_history': st.session_state.get('local_task_history', [])
        }
    
    try:
        doc_ref = db.collection('users').document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        st.warning(f"Error fetching history: {str(e)}. Using local storage.")
        return {
            'mood_history': st.session_state.get('local_mood_history', []),
            'focus_history': st.session_state.get('local_focus_history', []),
            'task_history': st.session_state.get('local_task_history', [])
        }
    return None

def update_user_history(db, user_id, activity_type, data):
    """Update user history in Firestore"""
    if not is_firestore_available():
        # Fallback to session state
        if f'local_{activity_type}_history' not in st.session_state:
            st.session_state[f'local_{activity_type}_history'] = []
        st.session_state[f'local_{activity_type}_history'].append(data)
        return

    try:
        doc_ref = db.collection('users').document(user_id)
        
        # Add timestamp to the data
        data['timestamp'] = datetime.now().isoformat()
        data['activity_type'] = activity_type
        
        # Get current history
        doc = doc_ref.get()
        if doc.exists:
            current_data = doc.to_dict()
            history_array = current_data.get(f'{activity_type}_history', [])
            history_array.append(data)
            
            # Update Firestore
            doc_ref.update({
                f'{activity_type}_history': history_array
            })
            
            # Update session state as backup
            st.session_state[f'local_{activity_type}_history'] = history_array
        else:
            # Create new document with initial history
            doc_ref.set({
                f'{activity_type}_history': [data]
            })
            st.session_state[f'local_{activity_type}_history'] = [data]
            
    except Exception as e:
        st.warning(f"Failed to update database: {str(e)}. Using local storage.")
        if f'local_{activity_type}_history' not in st.session_state:
            st.session_state[f'local_{activity_type}_history'] = []
        st.session_state[f'local_{activity_type}_history'].append(data)

def render_history_dashboard(storage_service: StorageService, user_id: str):
    """Render the history dashboard with latest data"""
    st.title("📊 Activity History")
    
    # Force sync before displaying history
    storage_service.sync_user_data(user_id)
    
    # Get complete user history
    user_data = storage_service.get_user_history(user_id)
    
    # Display filters
    col1, col2 = st.columns(2)
    with col1:
        time_filter = st.selectbox(
            "Time Period",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"]
        )
    with col2:
        activity_type = st.multiselect(
            "Activity Type",
            ["Mood", "Tasks", "Focus Sessions"],
            default=["Mood", "Tasks", "Focus Sessions"]
        )
    
    # Convert time filter to days
    days_map = {
        "Last 7 Days": 7,
        "Last 30 Days": 30,
        "Last 90 Days": 90,
        "All Time": None
    }
    days_filter = days_map[time_filter]
    
    # Get filtered data
    filtered_data = storage_service._filter_history(user_data, days_filter, None)
    
    # Display activity summaries
    if "Mood" in activity_type and filtered_data.get('mood_history'):
        st.subheader("Mood History")
        render_mood_history(filtered_data.get('mood_history', []), datetime.now() - timedelta(days=7))
    
    if "Tasks" in activity_type and filtered_data.get('task_history'):
        st.subheader("Task History")
        render_task_history(filtered_data.get('task_history', []), datetime.now() - timedelta(days=7))
    
    if "Focus Sessions" in activity_type and filtered_data.get('focus_history'):
        st.subheader("Focus Sessions")
        render_focus_history(filtered_data.get('focus_history', []), datetime.now() - timedelta(days=7))

def render_mood_history(mood_history, start_date=None):
    if not mood_history:
        st.info("No mood history available.")
        return

    df = pd.DataFrame(mood_history)
    # Convert timestamps to pandas datetime (with UTC awareness)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

    st.dataframe(df)

def render_focus_history(focus_history, start_date):
    st.subheader("🎯 Focus Sessions")
    
    if not focus_history:
        st.info("No focus session data available yet.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(focus_history)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df[df['timestamp'] >= start_date]

    # Focus session statistics
    total_sessions = len(df)
    total_minutes = df['duration'].sum()
    avg_session_length = total_minutes / total_sessions if total_sessions > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sessions", total_sessions)
    col2.metric("Total Minutes", f"{total_minutes:.0f}")
    col3.metric("Avg. Session Length", f"{avg_session_length:.1f} min")

def render_task_history(task_history, start_date):
    st.subheader("✅ Task Completion")
    
    if not task_history:
        st.info("No task completion data available yet.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(task_history)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df[df['timestamp'] >= start_date]

    # Task completion statistics
    total_tasks = len(df)
    completed_tasks = len(df[df['status'] == 'completed'])
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tasks", total_tasks)
    col2.metric("Completed Tasks", completed_tasks)
    col3.metric("Completion Rate", f"{completion_rate:.1f}%")

def calculate_streak(user_data):
    # Combine all activities
    all_activities = []
    for activity_type in ['mood_history', 'focus_history', 'task_history']:
        activities = user_data.get(activity_type, [])
        all_activities.extend([(datetime.fromisoformat(a['timestamp']).date(), 1) for a in activities])

    if not all_activities:
        return 0

    # Sort activities by date
    all_activities.sort(reverse=True)
    dates = [date for date, _ in all_activities]
    
    # Calculate streak
    streak = 1
    current_date = dates[0]
    
    for date in dates[1:]:
        if date == current_date - timedelta(days=1):
            streak += 1
            current_date = date
        else:
            break
    
    return streak 