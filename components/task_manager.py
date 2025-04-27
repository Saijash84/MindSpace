import streamlit as st
from datetime import datetime, timedelta, time
import json
from groq import Groq
import os
from services.storage_service import StorageService

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

def render_task_manager(storage_service: StorageService):
    """Main function to render the task manager interface"""
    st.title("📝 Task Manager")

    # Initialize task list in session state if not exists
    if 'tasks' not in st.session_state:
        st.session_state.tasks = []

    # Add new task
    with st.form("new_task_form", clear_on_submit=True):
        task_title = st.text_input("Task Title")
        task_description = st.text_area("Description")
        task_priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        due_date = st.date_input("Due Date")
        
        if st.form_submit_button("Add Task"):
            new_task = {
                "id": str(datetime.now().timestamp()),  # Add unique ID
                "title": task_title,
                "description": task_description,
                "priority": task_priority,
                "due_date": due_date.isoformat(),
                "status": "pending",
                "timestamp": datetime.now().isoformat()
            }
            
            # Save to storage
            user_id = st.session_state.get('user_id')
            if user_id:
                try:
                    storage_service.save_task_entry(user_id, new_task)
                    st.success("Task added successfully!")
                except Exception as e:
                    st.error(f"Error saving task: {str(e)}")

    # Display tasks
    st.subheader("Your Tasks")
    
    # Get tasks from storage
    user_id = st.session_state.get('user_id')
    if user_id:
        try:
            user_data = storage_service.get_user_history(user_id)
            tasks = user_data.get('task_history', [])
            
            if not tasks:
                st.info("No tasks found. Add some tasks to get started!")
            else:
                # Filter options
                status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Completed"])
                priority_filter = st.selectbox("Filter by Priority", ["All", "High", "Medium", "Low"])
                
                # Apply filters
                filtered_tasks = tasks
                if status_filter != "All":
                    filtered_tasks = [t for t in filtered_tasks if t['status'].lower() == status_filter.lower()]
                if priority_filter != "All":
                    filtered_tasks = [t for t in filtered_tasks if t['priority'] == priority_filter]
                
                # Display tasks
                for index, task in enumerate(filtered_tasks):
                    # Create a unique key using index and timestamp
                    unique_key = f"{task['timestamp']}_{index}"
                    
                    with st.expander(f"{task['title']} ({task['priority']})"):
                        st.write(f"Description: {task['description']}")
                        st.write(f"Due Date: {task['due_date']}")
                        st.write(f"Status: {task['status']}")
                        
                        # Status update button with unique key
                        new_status = "completed" if task['status'] == "pending" else "pending"
                        if st.button(f"Mark as {new_status}", 
                                   key=f"status_{unique_key}"):  # Using unique key
                            task['status'] = new_status
                            storage_service.update_task_status(user_id, task)
                            st.rerun()
                        
                        # Delete button with unique key
                        if st.button("Delete Task", 
                                   key=f"delete_{unique_key}"):  # Using unique key
                            storage_service.delete_task(user_id, task)
                            st.rerun()
                            
        except Exception as e:
            st.error(f"Error loading tasks: {str(e)}")
            st.info("Using local storage as fallback")

    # Schedule Generation Section
    st.subheader("📅 Generate Daily Schedule")
    
    # Get active tasks
    active_tasks = [t for t in tasks if t['status'] == 'pending']
    
    if not active_tasks:
        st.info("Add some pending tasks to generate a schedule!")
    else:
        with st.expander("Schedule Preferences"):
            col1, col2 = st.columns(2)
            with col1:
                work_start = st.time_input("Work Start Time", value=datetime.strptime("09:00", "%H:%M").time())
                work_end = st.time_input("Work End Time", value=datetime.strptime("17:00", "%H:%M").time())
            with col2:
                break_duration = st.number_input("Break Duration (minutes)", min_value=5, max_value=60, value=15)
                preferred_task_duration = st.number_input("Preferred Task Duration (minutes)", 
                                                        min_value=15, max_value=180, value=45)

        if st.button("Generate Schedule"):
            with st.spinner("Generating optimal schedule..."):
                # Prepare tasks for AI
                task_list = [{
                    "title": task['title'],
                    "description": task['description'],
                    "priority": task['priority'],
                    "due_date": task['due_date']
                } for task in active_tasks]

                preferences = {
                    "work_start": work_start.strftime("%H:%M"),
                    "work_end": work_end.strftime("%H:%M"),
                    "break_duration": break_duration,
                    "preferred_task_duration": preferred_task_duration
                }

                # Generate schedule using TaskManager's generate_schedule method
                schedule = task_manager.generate_schedule(task_list, preferences)
                
                if schedule:
                    st.success("Schedule generated successfully!")
                    st.markdown(schedule)
                    
                    # Save generated schedule
                    schedule_data = {
                        "date": datetime.now().date().isoformat(),
                        "tasks": task_list,
                        "preferences": preferences,
                        "generated_schedule": schedule
                    }
                    storage_service.save_schedule(user_id, schedule_data) 