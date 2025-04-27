import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from firebase_admin import firestore, auth
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import random
import string
import pandas as pd

class StorageService:
    def __init__(self, db):
        self.db = db
        self.local_storage_path = "data"
        self._ensure_local_storage_exists()

    def _ensure_local_storage_exists(self):
        """Create local storage directory if it doesn't exist"""
        if not os.path.exists(self.local_storage_path):
            os.makedirs(self.local_storage_path)

    def _get_user_file_path(self, user_id: str) -> str:
        """Get path to user's local storage file"""
        return os.path.join(self.local_storage_path, f"user_{user_id}.json")

    def _load_local_data(self, user_id: str) -> Dict:
        """Load user data from local storage"""
        file_path = self._get_user_file_path(user_id)
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return {
            'mood_history': [],
            'focus_history': [],
            'task_history': [],
            'chat_history': [],
            'settings': {'theme': 'light'}
        }

    def _save_local_data(self, user_id: str, data: Dict):
        """Save user data to local storage"""
        file_path = self._get_user_file_path(user_id)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def is_firestore_available(self) -> bool:
        """Check if Firestore is available"""
        try:
            if not self.db:
                return False
            # Try a simple operation
            self.db.collection('test').limit(1).get()
            return True
        except Exception:
            return False

    def save_mood_entry(self, user_id: str, mood_data: Dict[str, Any]) -> bool:
        """Save mood entry to storage"""
        try:
            if self.is_firestore_available():
                # Save to Firestore
                doc_ref = self.db.collection('users').document(user_id)
                doc_ref.update({
                    'mood_history': firestore.ArrayUnion([{
                        **mood_data,
                        'timestamp': datetime.now()
                    }])
                })
            else:
                # Save to local storage
                data = self._load_local_data(user_id)
                data['mood_history'].append({
                    **mood_data,
                    'timestamp': datetime.now().isoformat()
                })
                self._save_local_data(user_id, data)
            return True
        except Exception as e:
            st.warning(f"Storage error: {str(e)}")
            return False

    def get_user_history(
        self, 
        user_id: str, 
        days: Optional[int] = None,
        mood_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user history from storage"""
        try:
            if self.is_firestore_available():
                # Get from Firestore
                doc = self.db.collection('users').document(user_id).get()
                if doc.exists:
                    data = doc.to_dict()
                else:
                    data = self._load_local_data(user_id)
            else:
                # Get from local storage
                data = self._load_local_data(user_id)

            # Apply filters
            if days or mood_filter:
                data = self._filter_history(data, days, mood_filter)
            
            return data
        except Exception as e:
            st.warning(f"Error fetching history: {str(e)}")
            return self._load_local_data(user_id)

    def _filter_history(
        self, 
        data: Dict[str, Any], 
        days: Optional[int], 
        mood_filter: Optional[str]
    ) -> Dict[str, Any]:
        """Apply filters to history data"""
        filtered_data = data.copy()
        
        for history_type in ['mood_history', 'focus_history', 'task_history']:
            if history_type in filtered_data:
                history = filtered_data[history_type]
                
                # Filter by days
                if days:
                    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
                    def parse_timestamp(ts):
                        if isinstance(ts, datetime):
                            if ts.tzinfo is None:
                                return ts.replace(tzinfo=timezone.utc)
                            return ts.astimezone(timezone.utc)
                        elif isinstance(ts, str):
                            try:
                                dt = datetime.fromisoformat(ts)
                                if dt.tzinfo is None:
                                    return dt.replace(tzinfo=timezone.utc)
                                return dt.astimezone(timezone.utc)
                            except Exception:
                                return None
                        else:
                            return None

                    history = [
                        entry for entry in history
                        if (parse_timestamp(entry.get('timestamp')) is not None and
                            parse_timestamp(entry.get('timestamp')) >= cutoff)
                    ]
                
                # Filter by mood
                if mood_filter and history_type == 'mood_history':
                    history = [
                        entry for entry in history
                        if entry['mood'] in mood_filter
                    ]
                
                filtered_data[history_type] = history
        
        return filtered_data

    def update_user_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """Update user settings"""
        try:
            if self.is_firestore_available():
                self.db.collection('users').document(user_id).update({
                    'settings': settings
                })
            else:
                data = self._load_local_data(user_id)
                data['settings'] = settings
                self._save_local_data(user_id, data)
            return True
        except Exception as e:
            st.warning(f"Error updating settings: {str(e)}")
            return False

    def save_task_entry(self, user_id: str, task_data: Dict[str, Any]) -> bool:
        """Save task entry to storage"""
        try:
            if self.is_firestore_available():
                doc_ref = self.db.collection('users').document(user_id)
                doc_ref.update({
                    'task_history': firestore.ArrayUnion([task_data])
                })
            else:
                data = self._load_local_data(user_id)
                data['task_history'].append(task_data)
                self._save_local_data(user_id, data)
            return True
        except Exception as e:
            st.warning(f"Storage error: {str(e)}")
            return False

    def update_task_status(self, user_id: str, task: Dict[str, Any]) -> bool:
        """Update task status in storage"""
        try:
            if self.is_firestore_available():
                doc_ref = self.db.collection('users').document(user_id)
                doc = doc_ref.get()
                if doc.exists:
                    tasks = doc.to_dict().get('task_history', [])
                    tasks = [t if t.get('id') != task['id'] else task for t in tasks]
                    doc_ref.update({'task_history': tasks})
            else:
                data = self._load_local_data(user_id)
                data['task_history'] = [t if t.get('id') != task['id'] else task 
                                      for t in data['task_history']]
                self._save_local_data(user_id, data)
            return True
        except Exception as e:
            st.warning(f"Error updating task: {str(e)}")
            return False

    def delete_task(self, user_id: str, task: Dict[str, Any]) -> bool:
        """Delete task from storage"""
        try:
            if self.is_firestore_available():
                doc_ref = self.db.collection('users').document(user_id)
                doc = doc_ref.get()
                if doc.exists:
                    tasks = doc.to_dict().get('task_history', [])
                    tasks = [t for t in tasks if t.get('id') != task['id']]
                    doc_ref.update({'task_history': tasks})
            else:
                data = self._load_local_data(user_id)
                data['task_history'] = [t for t in data['task_history'] 
                                      if t.get('id') != task['id']]
                self._save_local_data(user_id, data)
            return True
        except Exception as e:
            st.warning(f"Error deleting task: {str(e)}")
            return False

    def save_focus_entry(self, user_id: str, focus_data: Dict[str, Any]) -> bool:
        """Save focus session entry to storage"""
        try:
            if self.is_firestore_available():
                doc_ref = self.db.collection('users').document(user_id)
                doc_ref.update({
                    'focus_history': firestore.ArrayUnion([focus_data])
                })
            else:
                data = self._load_local_data(user_id)
                data['focus_history'].append(focus_data)
                self._save_local_data(user_id, data)
            return True
        except Exception as e:
            st.warning(f"Storage error: {str(e)}")
            return False

    def save_schedule(self, user_id: str, schedule_data: Dict[str, Any]) -> bool:
        """Save generated schedule to storage"""
        try:
            if self.is_firestore_available():
                doc_ref = self.db.collection('users').document(user_id)
                doc_ref.update({
                    'schedules': firestore.ArrayUnion([schedule_data])
                })
            else:
                data = self._load_local_data(user_id)
                if 'schedules' not in data:
                    data['schedules'] = []
                data['schedules'].append(schedule_data)
                self._save_local_data(user_id, data)
            return True
        except Exception as e:
            st.warning(f"Error saving schedule: {str(e)}")
            return False

    def cleanup_old_data(self, user_id: str) -> bool:
        """Clean up data older than 1 year"""
        try:
            if self.is_firestore_available():
                doc_ref = self.db.collection('users').document(user_id)
                doc = doc_ref.get()
                if doc.exists:
                    data = doc.to_dict()
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=365)
                    
                    # Clean up each history type
                    for history_type in ['mood_history', 'focus_history', 'task_history', 'schedules']:
                        if history_type in data:
                            data[history_type] = [
                                entry for entry in data[history_type]
                                if datetime.fromisoformat(entry['timestamp']) > cutoff_date
                            ]
                    
                    # Update document with cleaned data
                    doc_ref.set(data)
            return True
        except Exception as e:
            st.warning(f"Error cleaning up old data: {str(e)}")
            return False

    def send_otp(self, email: str) -> str:
        """Send OTP to user's email"""
        try:
            # Generate OTP
            otp = ''.join(random.choices(string.digits, k=6))
            
            # First try storing OTP locally if Firestore is not available
            otp_data = {
                'otp': otp,
                'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
                'attempts': 0
            }
            
            if self.is_firestore_available():
                try:
                    otp_ref = self.db.collection('otps').document(email)
                    otp_ref.set(otp_data)
                except Exception as e:
                    st.warning(f"Firestore storage failed, using local storage: {str(e)}")
                    self._save_local_data(f"otp_{email}", otp_data)
            else:
                self._save_local_data(f"otp_{email}", otp_data)
            
            # Email configuration
            smtp_server = "smtp.gmail.com"
            smtp_port = 587
            
            try:
                sender_email = st.secrets["EMAIL_ADDRESS"]
                sender_password = st.secrets["EMAIL_PASSWORD"]
                
                # Verify email credentials format
                if not sender_email or not sender_password:
                    raise ValueError("Email credentials are missing")
                if len(sender_password) != 16:
                    raise ValueError("App Password should be exactly 16 characters")
                
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = email
                msg['Subject'] = "MindSpace - Your Verification Code"
                
                # Simplified HTML template
                html = f"""
                <div style="padding: 20px; background-color: #f9f9f9;">
                    <h2>Your MindSpace Verification Code</h2>
                    <div style="font-size: 24px; padding: 20px; background-color: #ffffff; margin: 20px 0;">
                        <strong>{otp}</strong>
                    </div>
                    <p>This code will expire in 10 minutes.</p>
                </div>
                """
                
                msg.attach(MIMEText(html, 'html'))
                
                # Detailed error handling for SMTP
                try:
                    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                        server.starttls()
                        st.info("Attempting to send verification code...")
                        server.login(sender_email, sender_password)
                        server.send_message(msg)
                        st.success("Verification code sent successfully!")
                    return otp
                except smtplib.SMTPAuthenticationError:
                    st.error("""Email authentication failed. Please check:
                    1. Email address is correct
                    2. App Password is correct (16 characters, no spaces)
                    3. 2-Step Verification is enabled
                    """)
                except smtplib.SMTPException as smtp_error:
                    st.error(f"SMTP error: {str(smtp_error)}")
                except Exception as e:
                    st.error(f"Failed to send email: {str(e)}")
            except Exception as e:
                st.error(f"Email configuration error: {str(e)}")
            
            return None
        except Exception as e:
            st.error(f"Error in send_otp: {str(e)}")
            return None

    def verify_otp(self, email: str, otp: str) -> bool:
        """Verify OTP"""
        try:
            # Try Firestore first
            if self.is_firestore_available():
                try:
                    otp_ref = self.db.collection('otps').document(email)
                    otp_doc = otp_ref.get()
                    
                    if otp_doc.exists:
                        otp_data = otp_doc.to_dict()
                        expires_at = datetime.fromisoformat(otp_data['expires_at'])
                        
                        if datetime.now(timezone.utc) > expires_at:
                            st.error("Verification code has expired. Please request a new one.")
                            return False
                        
                        if otp_data['otp'] == otp:
                            # Clean up OTP document after successful verification
                            otp_ref.delete()
                            return True
                        else:
                            st.error("Invalid verification code.")
                            return False
                except Exception:
                    st.warning("Firestore verification failed, checking local storage...")
            
            # Fallback to local storage
            try:
                otp_data = self._load_local_data(f"otp_{email}")
                if otp_data:
                    expires_at = datetime.fromisoformat(otp_data['expires_at'])
                    
                    if datetime.now(timezone.utc) > expires_at:
                        st.error("Verification code has expired. Please request a new one.")
                        return False
                    
                    if otp_data['otp'] == otp:
                        # Clean up local OTP data
                        self._save_local_data(f"otp_{email}", None)
                        return True
                    else:
                        st.error("Invalid verification code.")
                return False
            except Exception as e:
                st.error(f"Error verifying OTP: {str(e)}")
                return False
            
        except Exception as e:
            st.error(f"Error in verify_otp: {str(e)}")
            return False

    def sync_user_data(self, user_id: str) -> bool:
        """Synchronize user data between local storage and Firestore"""
        try:
            if self.is_firestore_available():
                # Get local data
                local_data = self._load_local_data(user_id)
                
                # Get Firestore data
                doc_ref = self.db.collection('users').document(user_id)
                doc = doc_ref.get()
                
                if doc.exists:
                    firestore_data = doc.to_dict()
                    
                    # Merge data (prefer Firestore data but include any local-only entries)
                    merged_data = firestore_data.copy()
                    
                    for history_type in ['mood_history', 'focus_history', 'task_history', 'chat_history']:
                        local_entries = local_data.get(history_type, [])
                        firestore_entries = firestore_data.get(history_type, [])
                        
                        # Create sets of entry IDs for comparison
                        local_ids = {entry.get('id') for entry in local_entries if entry.get('id')}
                        firestore_ids = {entry.get('id') for entry in firestore_entries if entry.get('id')}
                        
                        # Add local entries that don't exist in Firestore
                        new_entries = [entry for entry in local_entries 
                                     if entry.get('id') and entry.get('id') not in firestore_ids]
                        
                        if new_entries:
                            merged_data[history_type] = firestore_entries + new_entries
                            # Update Firestore with merged data
                            doc_ref.update({history_type: merged_data[history_type]})
                    
                    # Update local storage with merged data
                    self._save_local_data(user_id, merged_data)
                    
                    return True
            return False
        except Exception as e:
            st.warning(f"Error syncing data: {str(e)}")
            return False

    def update_user_profile(self, user_id: str, bio: str, interests: list):
        """Update user's bio and interests"""
        try:
            if self.is_firestore_available():
                self.db.collection('users').document(user_id).update({
                    'profile.bio': bio,
                    'profile.interests': interests
                })
            else:
                data = self._load_local_data(user_id)
                if 'profile' not in data:
                    data['profile'] = {}
                data['profile']['bio'] = bio
                data['profile']['interests'] = interests
                self._save_local_data(user_id, data)
            return True
        except Exception as e:
            st.error(f"Error updating profile: {str(e)}")
            return False

    def get_user_profile(self, user_id: str):
        """Get user's profile"""
        try:
            if self.is_firestore_available():
                doc = self.db.collection('users').document(user_id).get()
                if doc.exists:
                    return doc.to_dict().get('profile', {})
            else:
                data = self._load_local_data(user_id)
                return data.get('profile', {})
        except Exception as e:
            st.error(f"Error fetching profile: {str(e)}")
            return {}

    def get_or_create_chat(self, user_id1: str, user_id2: str):
        """Get or create a chat between two users"""
        try:
            if self.is_firestore_available():
                chats = self.db.collection('buddy_chats').where('participants', 'in', [
                    [user_id1, user_id2], [user_id2, user_id1]
                ]).stream()
                for chat in chats:
                    return chat.id
                # Create new chat
                chat_ref = self.db.collection('buddy_chats').document()
                chat_ref.set({
                    'participants': [user_id1, user_id2],
                    'messages': []
                })
                return chat_ref.id
            else:
                # Local fallback: not implemented for brevity
                return None
        except Exception as e:
            st.error(f"Error getting/creating chat: {str(e)}")
            return None

    def send_buddy_message(self, chat_id: str, sender_id: str, msg_type: str, content: str):
        """Send a message in a buddy chat"""
        try:
            if self.is_firestore_available():
                chat_ref = self.db.collection('buddy_chats').document(chat_id)
                chat_ref.update({
                    'messages': firestore.ArrayUnion([{
                        'sender': sender_id,
                        'type': msg_type,
                        'content': content,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }])
                })
                return True
            else:
                # Local fallback: not implemented for brevity
                return False
        except Exception as e:
            st.error(f"Error sending message: {str(e)}")
            return False

    def get_buddy_messages(self, chat_id: str):
        """Get all messages in a buddy chat"""
        try:
            if self.is_firestore_available():
                chat_ref = self.db.collection('buddy_chats').document(chat_id)
                doc = chat_ref.get()
                if doc.exists:
                    return doc.to_dict().get('messages', [])
            else:
                # Local fallback: not implemented for brevity
                return []
        except Exception as e:
            st.error(f"Error fetching messages: {str(e)}")
            return [] 