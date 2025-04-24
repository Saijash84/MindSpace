import streamlit as st
from datetime import datetime, timedelta, time
import json
from groq import Groq
import os

class TimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, time):
            return obj.strftime("%H:%M")
        return super().default(obj)

class TaskManager:
    def __init__(self):
        # Try to get API key from environment variable first
        api_key = os.getenv("GROQ_API_KEY")
        
        # If not in environment, try secrets
        if not api_key and "GROQ_API_KEY" in st.secrets:
            api_key = st.secrets["GROQ_API_KEY"]
            
        if not api_key:
            st.error("""
            Groq API key not found. Please set it up in one of these ways:
            
            1. Set as environment variable:
               - Windows: `set GROQ_API_KEY=your-key-here`
               - Linux/Mac: `export GROQ_API_KEY=your-key-here`
            
            2. Or add to secrets.toml:
               ```
               GROQ_API_KEY = "your-key-here"
               ```
            
            Get your API key from https://console.groq.com/
            """)
            return
            
        try:
            self.client = Groq(api_key=api_key)
            self.model = "llama3-70b-8192"  # Using the latest recommended model
        except Exception as e:
            st.error(f"Error initializing Groq client: {e}")
            return

    def generate_schedule(self, tasks, preferences):
        try:
            system_message = """You are an AI task scheduler that helps users organize their tasks efficiently.
            - Create a realistic and balanced schedule
            - Consider task priorities and deadlines
            - Include breaks and buffer time
            - Suggest optimal time slots for each task
            - Provide clear time allocations
            - Ensure the schedule is flexible and manageable
            - Include motivational messages and tips"""
            
            prompt = f"""Create a daily schedule based on these tasks and preferences:
            
            Tasks:
            {json.dumps(tasks, indent=2, cls=TimeEncoder)}
            
            Preferences:
            {json.dumps(preferences, indent=2, cls=TimeEncoder)}
            
            Please provide:
            1. A time-based schedule for the day
            2. Suggested time slots for each task
            3. Break times
            4. Any additional tips or recommendations"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                presence_penalty=0.6,
                frequency_penalty=0.6
            )

            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Error generating schedule: {e}")
            return None

    def save_task(self, task):
        if 'tasks' not in st.session_state:
            st.session_state.tasks = []
            
        task['id'] = len(st.session_state.tasks) + 1
        task['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task['completed'] = False
        
        st.session_state.tasks.append(task)

    def get_tasks(self):
        return st.session_state.get('tasks', [])

    def update_task(self, task_id, updates):
        tasks = st.session_state.get('tasks', [])
        for task in tasks:
            if task['id'] == task_id:
                task.update(updates)
                break

def render_task_manager():
    st.subheader("📝 Task Manager")
    
    task_manager = TaskManager()
    
    # Initialize tasks in session state
    if 'tasks' not in st.session_state:
        st.session_state.tasks = []
    
    # Task input form
    with st.form("task_form"):
        st.write("Add a new task")
        title = st.text_input("Task Title")
        description = st.text_area("Description")
        priority = st.selectbox("Priority", ["Low", "Medium", "High"])
        due_date = st.date_input("Due Date")
        
        submitted = st.form_submit_button("Add Task")
        if submitted and title:
            task_manager.save_task({
                'title': title,
                'description': description,
                'priority': priority,
                'due_date': due_date.strftime("%Y-%m-%d")
            })
            st.rerun()
    
    # Display tasks
    st.write("---")
    st.write("📋 Your Tasks")
    
    tasks = task_manager.get_tasks()
    if tasks:
        for task in tasks:
            with st.expander(f"{task['title']} - {task['priority']} Priority"):
                st.write(f"Description: {task['description']}")
                st.write(f"Due Date: {task['due_date']}")
                st.write(f"Created: {task['created_at']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Mark Complete", key=f"complete_{task['id']}"):
                        task_manager.update_task(task['id'], {'completed': True})
                        st.rerun()
                with col2:
                    if st.button("Delete", key=f"delete_{task['id']}"):
                        st.session_state.tasks = [t for t in tasks if t['id'] != task['id']]
                        st.rerun()
    else:
        st.info("No tasks added yet. Add a task using the form above!")
    
    # Schedule generation
    st.write("---")
    st.write("📅 Generate Schedule")
    
    if tasks:
        preferences = {
            "work_hours": st.time_input("Preferred Work Hours Start", value=datetime.strptime("09:00", "%H:%M").time()),
            "break_duration": st.number_input("Break Duration (minutes)", min_value=5, max_value=60, value=15),
            "focus_areas": st.multiselect("Focus Areas", ["Work", "Study", "Exercise", "Personal", "Other"])
        }
        
        if st.button("Generate Schedule"):
            with st.spinner("Creating your schedule..."):
                schedule = task_manager.generate_schedule(tasks, preferences)
                if schedule:
                    st.write("---")
                    st.write(schedule)
    else:
        st.warning("Add some tasks first to generate a schedule!") 