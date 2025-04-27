import streamlit as st
import firebase_admin
from firebase_admin import auth, credentials, firestore
from components.mood_bot import render_mood_check_in
from components.task_manager import render_task_manager
from components.focus_mode import render_focus_mode
from components.story_generator import render_story_generator
from components.buddy_connect import render_buddy_connect
from components.history_tracker import render_history_dashboard, update_user_history
from datetime import datetime, timedelta
from config import (
    db,
    is_firestore_available,
    initialize_firebase,
    APP_NAME,
    APP_DESCRIPTION,
    EMERGENCY_CONTACTS,
)
from services.storage_service import StorageService
import json

# Try to get FIREBASE_CONFIG, but don't fail if it's missing
try:
    from config import FIREBASE_CONFIG
except ImportError:
    FIREBASE_CONFIG = None

# Initialize session state for user profiles
if 'user_profiles' not in st.session_state:
    st.session_state.user_profiles = {}

# Initialize session state for local history storage
if 'local_mood_history' not in st.session_state:
    st.session_state.local_mood_history = []
if 'local_focus_history' not in st.session_state:
    st.session_state.local_focus_history = []
if 'local_task_history' not in st.session_state:
    st.session_state.local_task_history = []

# Initialize UserHistory (assuming it's defined in your main app or a utils file)
class UserHistory:
    def __init__(self):
        self.mood_log = []

    def add_mood_checkin(self, mood, user_message=None, ai_response=None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "mood": mood,
            "user_message": user_message,
            "ai_response": ai_response
        }
        self.mood_log.append(entry)

    def get_history(self):
        return self.mood_log

# Initialize history object
if 'history' not in st.session_state:
    st.session_state.history = UserHistory()

# Initialize storage service
storage_service = StorageService(db)

def get_user_profile(user_id):
    """Get user profile from session state"""
    return st.session_state.user_profiles.get(user_id)

def update_user_profile(user_id, profile_data):
    """Update user profile in session state"""
    st.session_state.user_profiles[user_id] = profile_data
    return True

def handle_login(email, password):
    """Handle user login"""
    try:
        user = auth.get_user_by_email(email)
        st.session_state.user_id = user.uid
        st.session_state.user_email = user.email
        
        # Initialize or fetch user data from Firestore
        user_ref = db.collection('users').document(user.uid)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            # Create new user document if it doesn't exist
            initial_data = {
                'email': email,
                'name': email.split('@')[0],
                'created_at': datetime.now().isoformat(),
                'mood_history': [],
                'focus_history': [],
                'task_history': [],
                'chat_history': [],
                'settings': {
                    'theme': 'light',
                    'notifications_enabled': True
                },
                'last_login': datetime.now().isoformat()
            }
            user_ref.set(initial_data)
            # Set user profile in session state
            st.session_state.user_profiles[user.uid] = {
                'email': email,
                'name': email.split('@')[0],
                'created_at': initial_data['created_at']
            }
            # Initialize session state with empty data
            for key in ['chat_history', 'mood_history', 'focus_history', 'task_history']:
                st.session_state[key] = []
        else:
            # Load existing data into session state
            user_data = user_doc.to_dict()
            st.session_state.user_profile = {
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'created_at': user_data.get('created_at')
            }
            # Set user profile in session state
            st.session_state.user_profiles[user.uid] = {
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'created_at': user_data.get('created_at')
            }
            # Update session state with user data
            st.session_state.chat_history = user_data.get('chat_history', [])
            st.session_state.mood_history = user_data.get('mood_history', [])
            st.session_state.focus_history = user_data.get('focus_history', [])
            st.session_state.task_history = user_data.get('task_history', [])
            # Update last login
            user_ref.update({'last_login': datetime.now().isoformat()})
        
        return True
    except Exception as e:
        st.error(f"Login failed: {e}")
        return False

def handle_signup(email, password, name):
    """Handle user signup after OTP verification"""
    try:
        # Create user in Firebase
        user = auth.create_user(
            email=email,
            password=password,
            display_name=name
        )

        # Create user profile in Firestore
        db.collection('users').document(user.uid).set({
            'email': email,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'mood_history': [],
            'focus_history': [],
            'task_history': [],
            'schedules': [],
            'settings': {
                'theme': 'light',
                'notifications_enabled': True,
                'data_retention_days': 365
            },
            'profile': {
                'name': name,
                'email': email,
                'joined_date': datetime.now().isoformat(),
                'last_login': datetime.now().isoformat()
            }
        })

        return True
    except Exception as e:
        st.error(f"Signup failed: {e}")
        return False

def handle_logout():
    """Handle user logout and cleanup"""
    try:
        # Save all session data to Firestore before clearing
        if st.session_state.user_id:
            doc_ref = db.collection('users').document(st.session_state.user_id)
            doc_ref.update({
                'chat_history': st.session_state.get('chat_history', []),
                'mood_history': st.session_state.get('local_mood_history', []),
                'focus_history': st.session_state.get('local_focus_history', []),
                'task_history': st.session_state.get('local_task_history', [])
            })
    except Exception as e:
        st.warning(f"Failed to save data during logout: {str(e)}")
    finally:
        # Clear session state
        for key in ['user_id', 'chat_history', 'local_mood_history', 
                   'local_focus_history', 'local_task_history']:
            if key in st.session_state:
                del st.session_state[key]

def render_auth():
    """Render authentication forms"""
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted and email and password:
                if handle_login(email, password):
                    st.success("Login successful!")
                    st.rerun()

    with tab2:
        if 'signup_step' not in st.session_state:
            st.session_state.signup_step = 1

        if st.session_state.signup_step == 1:
            # Step 1: Collect user information
            with st.form("signup_form"):
                name = st.text_input("Full Name")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Register")

                if submitted:
                    if not all([name, email, password, confirm_password]):
                        st.error("Please fill in all fields.")
                    elif password != confirm_password:
                        st.error("Passwords do not match.")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    else:
                        # Store registration details in session state
                        st.session_state.signup_name = name
                        st.session_state.signup_email = email
                        st.session_state.signup_password = password
                        
                        # Send OTP
                        otp = storage_service.send_otp(email)
                        if otp:
                            st.session_state.signup_step = 2
                            st.rerun()
                        else:
                            st.error("Failed to send OTP. Please try again.")

        elif st.session_state.signup_step == 2:
            # Step 2: OTP Verification
            st.subheader("Email Verification")
            st.info(f"OTP has been sent to {st.session_state.signup_email}")
            
            with st.form("otp_verification"):
                otp_input = st.text_input("Enter OTP")
                resend_col, verify_col = st.columns([1, 2])
                
                with resend_col:
                    if st.form_submit_button("Resend OTP"):
                        otp = storage_service.send_otp(st.session_state.signup_email)
                        if otp:
                            st.success("New OTP sent!")
                            st.rerun()
                        else:
                            st.error("Failed to send OTP. Please try again.")
                
                with verify_col:
                    if st.form_submit_button("Verify OTP"):
                        if storage_service.verify_otp(st.session_state.signup_email, otp_input):
                            # Create user account
                            if handle_signup(
                                st.session_state.signup_email,
                                st.session_state.signup_password,
                                st.session_state.signup_name
                            ):
                                # Clear signup session state
                                for key in ['signup_step', 'signup_email', 'signup_password', 'signup_name']:
                                    if key in st.session_state:
                                        del st.session_state[key]
                                st.success("Account created successfully! Please log in.")
                                st.rerun()
                        else:
                            st.error("Invalid OTP. Please try again.")

            if st.button("← Back"):
                st.session_state.signup_step = 1
                st.rerun()

def init_sync_state():
    if 'last_sync' not in st.session_state:
        st.session_state.last_sync = datetime.now()
    if 'sync_interval' not in st.session_state:
        st.session_state.sync_interval = timedelta(minutes=5)

def check_and_sync_data():
    """Check if it's time to sync data and perform sync if needed"""
    if datetime.now() - st.session_state.last_sync > st.session_state.sync_interval:
        if st.session_state.get('user_id'):
            storage_service.sync_user_data(st.session_state.user_id)
            st.session_state.last_sync = datetime.now()

def main():
    st.set_page_config(
        page_title="MindSpace",
        page_icon="🧠",
        layout="wide"
    )

    # Sidebar for navigation
    st.sidebar.title("🧠 MindSpace")

    # Authentication
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None

    if st.session_state.user_id is None:
        # Create two columns for login and register buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔑 Login", use_container_width=True):
                st.session_state.auth_mode = "login"
                
        with col2:
            if st.button("✨ Register", use_container_width=True):
                st.session_state.auth_mode = "register"
        
        # Initialize auth_mode if not exists
        if 'auth_mode' not in st.session_state:
            st.session_state.auth_mode = "login"
            
        # Display the appropriate form based on auth_mode
        if st.session_state.auth_mode == "login":
            with st.form("login_form"):
                st.subheader("🔑 Login")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")

                if submitted and email and password:
                    if handle_login(email, password):
                        st.success("Login successful!")
                        st.rerun()
                        
            # Add a link to switch to registration
            if st.button("Don't have an account? Register here"):
                st.session_state.auth_mode = "register"
                st.rerun()
                
        else:  # Register mode
            if 'signup_step' not in st.session_state:
                st.session_state.signup_step = 1

            if st.session_state.signup_step == 1:
                with st.form("signup_form"):
                    st.subheader("✨ Create Account")
                    name = st.text_input("Full Name")
                    email = st.text_input("Email")
                    password = st.text_input("Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")
                    
                    # Add password requirements info
                    st.markdown("""
                    **Password Requirements:**
                    - At least 6 characters long
                    - Combination of letters and numbers recommended
                    """)
                    
                    submitted = st.form_submit_button("Register")

                    if submitted:
                        if not all([name, email, password, confirm_password]):
                            st.error("Please fill in all fields.")
                        elif password != confirm_password:
                            st.error("Passwords do not match.")
                        elif len(password) < 6:
                            st.error("Password must be at least 6 characters long.")
                        else:
                            with st.spinner("Sending verification code..."):
                                # Store registration details in session state
                                st.session_state.signup_name = name
                                st.session_state.signup_email = email
                                st.session_state.signup_password = password
                                
                                # Send OTP
                                otp = storage_service.send_otp(email)
                                if otp:
                                    st.session_state.signup_step = 2
                                    st.success("Verification code sent!")
                                    st.rerun()
                                else:
                                    st.error("Failed to send verification code. Please try again.")

            elif st.session_state.signup_step == 2:
                st.subheader("📧 Email Verification")
                st.info(f"A verification code has been sent to {st.session_state.signup_email}")
                
                with st.form("otp_verification"):
                    otp_input = st.text_input("Enter Verification Code")
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        resend = st.form_submit_button("Resend Code")
                    with col2:
                        verify = st.form_submit_button("Verify")
                    
                    if resend:
                        with st.spinner("Resending verification code..."):
                            otp = storage_service.send_otp(st.session_state.signup_email)
                            if otp:
                                st.success("New verification code sent!")
                                st.rerun()
                            else:
                                st.error("Failed to send verification code. Please try again.")
                    
                    if verify:
                        with st.spinner("Verifying..."):
                            if storage_service.verify_otp(st.session_state.signup_email, otp_input):
                                if handle_signup(
                                    st.session_state.signup_email,
                                    st.session_state.signup_password,
                                    st.session_state.signup_name
                                ):
                                    # Clear signup session state
                                    for key in ['signup_step', 'signup_email', 'signup_password', 'signup_name', 'auth_mode']:
                                        if key in st.session_state:
                                            del st.session_state[key]
                                    st.success("Account created successfully! Please log in.")
                                    st.session_state.auth_mode = "login"
                                    st.rerun()
                            else:
                                st.error("Invalid verification code. Please try again.")

                if st.button("← Back"):
                    st.session_state.signup_step = 1
                    st.rerun()
                    
            # Add a link to switch to login
            if st.button("Already have an account? Login here"):
                st.session_state.auth_mode = "login"
                st.rerun()
    else:
        user_profile = st.session_state.user_profiles.get(st.session_state.user_id)
        if user_profile:
            st.sidebar.success(f"Logged in as {user_profile.get('name', user_profile.get('email', 'User'))}")
        else:
            # fallback if profile is missing
            st.sidebar.success(f"Logged in as {st.session_state.get('user_email', 'User')}")
        if st.sidebar.button("Logout"):
            handle_logout()
            st.rerun()

    # Add database status indicator in sidebar
    if is_firestore_available():
        st.sidebar.success("📊 Database: Connected")
    else:
        st.sidebar.warning("📊 Database: Using Local Storage")
        st.sidebar.info("Your data will be stored locally until database connection is restored")

    # Navigation
    pages = {
        "Mood Bot": lambda: render_mood_check_in(storage_service),
        "Task Manager": lambda: render_task_manager(storage_service),
        "Focus Mode": lambda: render_focus_mode(storage_service),
        "Story Generator": render_story_generator,
        "History": lambda: render_history_dashboard(storage_service, st.session_state.user_id),
        "Buddy Connect": lambda: render_buddy_connect(storage_service, st.session_state.user_id)
    }

    selected_page = st.sidebar.radio("Go to", list(pages.keys()))

    # Main content
    st.title("MindSpace - Your Mental Wellness Companion")

    if st.session_state.user_id is None:
        st.warning("Please log in to access the features")
        return

    init_sync_state()
    check_and_sync_data()

    # Render selected page
    if pages[selected_page]:
        pages[selected_page]()
    else:
        st.info(f"The '{selected_page}' feature is under development.")

if __name__ == "__main__":
    main()