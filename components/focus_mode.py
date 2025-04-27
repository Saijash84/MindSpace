import streamlit as st
import time
from datetime import datetime, timedelta
from services.storage_service import StorageService

class FocusMode:
    def __init__(self):
        self.work_duration = 25 * 60  # 25 minutes in seconds
        self.break_duration = 5 * 60   # 5 minutes in seconds
        self.long_break_duration = 15 * 60  # 15 minutes in seconds
        self.sessions_before_long_break = 4

    def format_time(self, seconds):
        """Format seconds into MM:SS"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def run_timer(self, duration, timer_type="work"):
        """Run the timer with progress bar"""
        start_time = time.time()
        end_time = start_time + duration
        
        # Create a placeholder for the timer display
        timer_placeholder = st.empty()
        progress_placeholder = st.empty()
        
        while time.time() < end_time:
            remaining = int(end_time - time.time())
            progress = 1 - (remaining / duration)
            
            # Update timer display
            timer_placeholder.markdown(f"""
            <div style='text-align: center; font-size: 48px; font-weight: bold;'>
                {self.format_time(remaining)}
            </div>
            """, unsafe_allow_html=True)
            
            # Update progress bar
            progress_placeholder.progress(progress)
            
            # Add a small delay to prevent high CPU usage
            time.sleep(0.1)
        
        # Clear the placeholders
        timer_placeholder.empty()
        progress_placeholder.empty()
        
        # Play sound when timer ends
        st.audio("https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3", format="audio/mp3")
        
        if timer_type == "work":
            st.success("Time's up! Take a short break.")
        else:
            st.success("Break's over! Time to get back to work.")

def render_focus_mode(storage_service: StorageService):
    """Main function to render the focus mode interface"""
    st.title("🎯 Focus Mode")

    # Initialize session state for focus sessions
    if 'focus_active' not in st.session_state:
        st.session_state.focus_active = False
    if 'focus_start_time' not in st.session_state:
        st.session_state.focus_start_time = None

    # Focus session setup
    if not st.session_state.focus_active:
        with st.form("focus_setup"):
            task_description = st.text_input("What are you focusing on?")
            duration = st.slider("Session Duration (minutes)", 5, 120, 25)
            start_button = st.form_submit_button("Start Focus Session")

            if start_button and task_description:
                st.session_state.focus_active = True
                st.session_state.focus_start_time = datetime.now()
                st.session_state.focus_duration = duration
                st.session_state.focus_task = task_description
                
                # Save focus session start
                user_id = st.session_state.get('user_id')
                if user_id:
                    focus_data = {
                        "task": task_description,
                        "duration": duration,
                        "start_time": datetime.now().isoformat(),
                        "status": "active"
                    }
                    storage_service.save_focus_entry(user_id, focus_data)
                st.rerun()

    # Active focus session
    if st.session_state.focus_active:
        elapsed_time = datetime.now() - st.session_state.focus_start_time
        remaining_time = timedelta(minutes=st.session_state.focus_duration) - elapsed_time

        if remaining_time.total_seconds() <= 0:
            st.success("Focus session completed! 🎉")
            
            # Save completed session
            user_id = st.session_state.get('user_id')
            if user_id:
                focus_data = {
                    "task": st.session_state.focus_task,
                    "duration": st.session_state.focus_duration,
                    "start_time": st.session_state.focus_start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "status": "completed"
                }
                storage_service.save_focus_entry(user_id, focus_data)

            # Reset session state
            st.session_state.focus_active = False
            st.session_state.focus_start_time = None
            if st.button("Start New Session"):
                st.rerun()
        else:
            # Display timer
            mins, secs = divmod(remaining_time.seconds, 60)
            st.header(f"⏱️ {mins:02d}:{secs:02d}")
            st.write(f"Focusing on: {st.session_state.focus_task}")

            if st.button("End Session Early"):
                # Save interrupted session
                user_id = st.session_state.get('user_id')
                if user_id:
                    focus_data = {
                        "task": st.session_state.focus_task,
                        "duration": st.session_state.focus_duration,
                        "start_time": st.session_state.focus_start_time.isoformat(),
                        "end_time": datetime.now().isoformat(),
                        "status": "interrupted"
                    }
                    storage_service.save_focus_entry(user_id, focus_data)

                st.session_state.focus_active = False
                st.session_state.focus_start_time = None
                st.rerun()

    # Display focus history
    st.subheader("Focus History")
    user_id = st.session_state.get('user_id')
    if user_id:
        try:
            user_data = storage_service.get_user_history(user_id)
            focus_sessions = user_data.get('focus_history', [])
            
            if not focus_sessions:
                st.info("No focus sessions recorded yet. Start your first session!")
            else:
                # Filter options
                status_filter = st.selectbox("Filter by Status", 
                    ["All", "Completed", "Interrupted"])
                
                # Apply filters
                filtered_sessions = focus_sessions
                if status_filter != "All":
                    filtered_sessions = [s for s in filtered_sessions 
                                      if s['status'].lower() == status_filter.lower()]
                
                # Display sessions
                for session in filtered_sessions:
                    with st.expander(
                        f"{session['task']} ({session['duration']} mins) - {session['status']}"):
                        st.write(f"Started: {session['start_time']}")
                        if 'end_time' in session:
                            st.write(f"Ended: {session['end_time']}")
                        st.write(f"Status: {session['status']}")
                        
        except Exception as e:
            st.error(f"Error loading focus history: {str(e)}")
            st.info("Using local storage as fallback")

    # Tips for focus
    st.markdown("""
    ### Tips for Better Focus:
    - Find a quiet, comfortable workspace
    - Turn off notifications
    - Keep water nearby
    - Take regular breaks
    - Use the Pomodoro technique (25 minutes work, 5 minutes break)
    """) 