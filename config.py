import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st

# Load environment variables
load_dotenv()

# Firebase Configuration
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
}

def initialize_firebase():
    """Initialize Firebase with error handling"""
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate("firebase-credentials.json")
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.warning(f"Firebase initialization error: {str(e)}")
        return None

# Initialize Firestore with error handling
db = initialize_firebase()

# Function to check if Firestore is working
def is_firestore_available():
    """Check if Firestore is available and working"""
    if not db:
        return False
    try:
        # Try a simple operation
        db.collection('test').limit(1).get()
        return True
    except Exception:
        return False

# OpenRouter/LLM Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# App Settings
APP_NAME = "MindSpace"
APP_DESCRIPTION = "Student Mental Health & Productivity Platform"

# Mood Analysis Settings
MOOD_CATEGORIES = [
    "Very Positive",
    "Positive",
    "Neutral",
    "Negative",
    "Very Negative"
]

# Task Priority Levels
TASK_PRIORITIES = [
    "High",
    "Medium",
    "Low"
]

# Pomodoro Settings
POMODORO_WORK_MINUTES = 25
POMODORO_BREAK_MINUTES = 5
POMODORO_LONG_BREAK_MINUTES = 15
POMODORO_SESSIONS_BEFORE_LONG_BREAK = 4

# Forum Settings
MAX_POST_LENGTH = 500
MIN_REPORTS_FOR_REVIEW = 3

# Emergency Contacts
EMERGENCY_CONTACTS = {
    "National Crisis Line": "988",
    "Campus Security": "YOUR_CAMPUS_SECURITY_NUMBER",
    "Student Counseling": "YOUR_COUNSELING_NUMBER"
}

# Collection Names
COLLECTIONS = {
    "users": "users",
    "posts": "forum_posts",
    "events": "wellness_events",
    "moods": "mood_history",
    "tasks": "tasks"
} 