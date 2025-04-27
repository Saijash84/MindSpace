from firebase_admin import firestore
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class DatabaseService:
    def __init__(self):
        self.db = firestore.client()

    def create_user_profile(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Create new user profile in Firestore"""
        try:
            self.db.collection('users').document(user_id).set({
                **data,
                'created_at': datetime.now(),
                'mood_history': [],
                'focus_history': [],
                'task_history': [],
                'chat_history': [],
                'settings': {
                    'notifications_enabled': True,
                    'theme': 'light'
                }
            })
            return True
        except Exception:
            return False

    def save_mood_entry(self, user_id: str, mood_data: Dict[str, Any]) -> bool:
        """Save mood check-in entry"""
        try:
            doc_ref = self.db.collection('users').document(user_id)
            doc_ref.update({
                'mood_history': firestore.ArrayUnion([{
                    **mood_data,
                    'timestamp': datetime.now()
                }])
            })
            return True
        except Exception:
            return False

    def get_user_history(
        self, 
        user_id: str, 
        days: Optional[int] = None,
        mood_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user's activity history with optional filters"""
        try:
            doc = self.db.collection('users').document(user_id).get()
            if not doc.exists:
                return {}

            data = doc.to_dict()
            if days:
                cutoff = datetime.now() - timedelta(days=days)
                data['mood_history'] = [
                    entry for entry in data.get('mood_history', [])
                    if entry['timestamp'] >= cutoff
                ]

            if mood_filter:
                data['mood_history'] = [
                    entry for entry in data.get('mood_history', [])
                    if entry['mood'] == mood_filter
                ]

            return data
        except Exception:
            return {}

    def update_user_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """Update user settings"""
        try:
            self.db.collection('users').document(user_id).update({
                'settings': settings
            })
            return True
        except Exception:
            return False

    def delete_mood_entry(self, user_id: str, entry_timestamp: datetime) -> bool:
        """Delete specific mood entry"""
        try:
            doc_ref = self.db.collection('users').document(user_id)
            doc = doc_ref.get()
            if not doc.exists:
                return False

            mood_history = doc.to_dict().get('mood_history', [])
            mood_history = [
                entry for entry in mood_history
                if entry['timestamp'] != entry_timestamp
            ]

            doc_ref.update({'mood_history': mood_history})
            return True
        except Exception:
            return False 