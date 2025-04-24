import streamlit as st
import firebase_admin
from firebase_admin import auth, credentials
from components.mood_bot import render_mood_check_in
from components.task_manager import render_task_manager
from components.story_generator import render_story_generator
from components.history import UserHistory
from datetime import datetime, timedelta
from config import (
    FIREBASE_CONFIG,
    APP_NAME,
    APP_DESCRIPTION,
    EMERGENCY_CONTACTS,
    db
)
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string
import os

# Initialize Firebase Admin
try:
    firebase_admin.get_app()
except ValueError:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)

# Initialize session state for user profiles
if 'user_profiles' not in st.session_state:
    st.session_state.user_profiles = {}

# Initialize UserHistory
history = UserHistory()

# Session timeout in minutes
SESSION_TIMEOUT = 30

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS") or st.secrets.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") or st.secrets.get("EMAIL_PASSWORD")

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
        # First check if user exists
        try:
            user = auth.get_user_by_email(email)
        except auth.UserNotFoundError:
            st.error("Email not found. Please check your email address.")
            return False
        except Exception as e:
            st.error(f"Error checking user: {str(e)}")
            return False

        # If user exists, try to sign in
        try:
            # This is a placeholder - in a real app, you'd use Firebase Auth SDK
            # For now, we'll just check if the user exists
            st.session_state.user_id = user.uid
            st.session_state.user_email = user.email
            st.session_state.username = user.display_name or email.split('@')[0]
            return True
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
            return False

    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        return False

def handle_signup(email, password, name):
    """Handle user signup"""
    try:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=name
        )
        
        # Create user profile in Firestore
        db.collection('users').document(user.uid).set({
            'email': email,
            'name': name,
            'created_at': datetime.now(),
            'mood_history': [],
            'tasks': [],
            'interests': [],
            'buddy_connected': None
        })
        
        return True
    except Exception as e:
        st.error(f"Signup failed: {e}")
        return False

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
        with st.form("signup_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign Up")
            
            if submitted and name and email and password:
                if handle_signup(email, password, name):
                    st.success("Account created successfully! Please log in.")

def generate_verification_code():
    """Generate a random verification code"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

def send_verification_email(email, verification_code):
    """Send verification email to user"""
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        st.error("""
        Email configuration not found. Please set up your email credentials:
        
        1. Set up Gmail App Password:
           - Go to your Google Account settings
           - Navigate to Security > 2-Step Verification
           - Under "App passwords", select "Mail" and your device
           - Copy the generated 16-character password
        
        2. Set environment variables:
           - EMAIL_ADDRESS: Your Gmail address
           - EMAIL_PASSWORD: The generated App Password
        
        Or add to secrets.toml:
        ```
        EMAIL_ADDRESS = "your-email@gmail.com"
        EMAIL_PASSWORD = "your-16-character-app-password"
        ```
        """)
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg['Subject'] = "MindSpace - Email Verification"

        body = f"""
        Thank you for registering with MindSpace!
        
        Your verification code is: {verification_code}
        
        Please enter this code in the application to complete your registration.
        
        This code will expire in 30 minutes.
        
        If you didn't request this verification, please ignore this email.
        """
        
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Error sending verification email: {str(e)}")
        return False

def check_session():
    """Check if the session is still valid"""
    if 'last_activity' in st.session_state:
        last_activity = datetime.fromisoformat(st.session_state.last_activity)
        if datetime.now() - last_activity > timedelta(minutes=SESSION_TIMEOUT):
            # Session expired
            st.session_state.clear()
            st.warning("Your session has expired. Please log in again.")
            return False
    return True

def update_session():
    """Update the last activity timestamp"""
    st.session_state.last_activity = datetime.now().isoformat()

def register():
    """Handle user registration"""
    st.title("Register for MindSpace 🧠")
    
    with st.form("register_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Register")
        
        if submitted:
            if not all([username, email, password, confirm_password]):
                st.error("Please fill in all fields")
                return
                
            if password != confirm_password:
                st.error("Passwords do not match")
                return
                
            # Generate verification code
            verification_code = generate_verification_code()
            
            # Store registration data in session state
            st.session_state.registration_data = {
                'username': username,
                'email': email,
                'password': password,
                'verification_code': verification_code,
                'verification_time': datetime.now().isoformat()
            }
            
            # Send verification email
            if send_verification_email(email, verification_code):
                st.success("Verification email sent! Please check your inbox.")
                st.session_state.show_verification = True
                st.rerun()
            else:
                st.error("Failed to send verification email. Please try again.")

def verify_email():
    """Handle email verification"""
    st.title("Verify Your Email 🧠")
    
    if 'registration_data' not in st.session_state:
        st.error("No registration data found. Please register again.")
        st.session_state.show_verification = False
        st.rerun()
        return
    
    registration_data = st.session_state.registration_data
    verification_time = datetime.fromisoformat(registration_data['verification_time'])
    
    # Check if verification code has expired (30 minutes)
    if datetime.now() - verification_time > timedelta(minutes=30):
        st.error("Verification code has expired. Please register again.")
        st.session_state.show_verification = False
        st.rerun()
        return
    
    with st.form("verification_form"):
        code = st.text_input("Enter verification code")
        submitted = st.form_submit_button("Verify")
        
        if submitted:
            if code == registration_data['verification_code']:
                # Store user data (in a real app, this would be in a database)
                st.session_state.users = st.session_state.get('users', {})
                st.session_state.users[registration_data['email']] = {
                    'username': registration_data['username'],
                    'password': registration_data['password'],
                    'verified': True
                }
                
                st.success("Email verified successfully! You can now log in.")
                st.session_state.show_verification = False
                st.rerun()
            else:
                st.error("Invalid verification code")

def login():
    """Handle user login"""
    st.title("Login to MindSpace 🧠")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="Enter your email address")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if not email or not password:
                st.error("Please enter both email and password")
                return
                
            if handle_login(email, password):
                st.session_state.logged_in = True
                update_session()
                history.add_session("login")
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Login failed. Please check your credentials.")

def logout():
    """Handle user logout"""
    history.add_session("logout")
    st.session_state.clear()
    st.success("Logged out successfully!")
    st.rerun()

def main():
    # Page configuration
    st.set_page_config(
        page_title="MindSpace",
        page_icon="🧠",
        layout="wide"
    )

    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = datetime.now().isoformat()
    if 'show_verification' not in st.session_state:
        st.session_state.show_verification = False

    # Check session validity
    if not check_session():
        login()
        return

    # Update session activity
    update_session()

    # Show appropriate page based on state
    if st.session_state.show_verification:
        verify_email()
        return
        
    if not st.session_state.logged_in:
        # Show login/register options
        tab1, tab2 = st.tabs(["Login", "Register"])
        with tab1:
            login()
        with tab2:
            register()
        return

    # Main application
    st.sidebar.title("🧠 MindSpace")
    
    # Display username and logout button in sidebar
    st.sidebar.write(f"Welcome, {st.session_state.username}!")
    if st.sidebar.button("Logout"):
        logout()
        return

    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Home", "Mood Check-In", "Task Manager", "Story Generator", "History"],
        index=0
    )

    # Main content area
    if page == "Home":
        st.title("Welcome to MindSpace 🧠")
        st.write("""
        Your personal mental wellness companion. Choose a feature from the sidebar to get started:
        
        - **Mood Check-In**: Track and understand your emotions
        - **Task Manager**: Organize your tasks and boost productivity
        - **Story Generator**: Get inspired with personalized stories
        - **History**: View your activity history and progress
        """)

    elif page == "Mood Check-In":
        render_mood_check_in(history)

    elif page == "Task Manager":
        render_task_manager(history)

    elif page == "Story Generator":
        render_story_generator(history)

    elif page == "History":
        history.render_history()

if __name__ == "__main__":
    main() 