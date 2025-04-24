import streamlit as st
import time
from datetime import datetime, timedelta

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

def render_focus_mode():
    st.subheader("🎯 Focus Mode")
    
    focus_mode = FocusMode()
    
    # Session settings
    col1, col2 = st.columns(2)
    with col1:
        work_time = st.number_input("Work Duration (minutes)", 1, 60, 25)
        focus_mode.work_duration = work_time * 60
    with col2:
        break_time = st.number_input("Break Duration (minutes)", 1, 30, 5)
        focus_mode.break_duration = break_time * 60
    
    # Session counter
    if 'session_count' not in st.session_state:
        st.session_state.session_count = 0
    
    # Timer controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Work Session"):
            st.session_state.session_count += 1
            focus_mode.run_timer(focus_mode.work_duration, "work")
            
            # Check if it's time for a long break
            if st.session_state.session_count % focus_mode.sessions_before_long_break == 0:
                st.info("You've completed several sessions! Time for a longer break.")
                if st.button("Start Long Break"):
                    focus_mode.run_timer(focus_mode.long_break_duration, "break")
            else:
                if st.button("Start Break"):
                    focus_mode.run_timer(focus_mode.break_duration, "break")
    
    # Session statistics
    st.markdown("---")
    st.write(f"Completed Sessions: {st.session_state.session_count}")
    
    # Tips for focus
    st.markdown("""
    ### Tips for Better Focus:
    - Find a quiet, comfortable workspace
    - Turn off notifications
    - Keep water nearby
    - Take regular breaks
    - Use the Pomodoro technique (25 minutes work, 5 minutes break)
    """) 