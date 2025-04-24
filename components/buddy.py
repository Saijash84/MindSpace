import streamlit as st
from datetime import datetime
import firebase_admin
from firebase_admin import firestore
from config import db
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class BuddySystem:
    def __init__(self):
        if 'buddy_state' not in st.session_state:
            st.session_state.buddy_state = {
                'current_chat': None,
                'chat_history': [],
                'last_refresh': None
            }

    def get_user_profile(self, user_id):
        """Get user profile from Firestore"""
        if not db:
            return None
            
        try:
            user_ref = db.collection('users').document(user_id)
            user = user_ref.get()
            return user.to_dict() if user.exists else None
        except Exception as e:
            st.error(f"Error retrieving user profile: {e}")
            return None

    def find_matches(self, user_id, limit=5):
        """Find potential buddy matches based on interests and mood"""
        if not db:
            return []
            
        try:
            # Get current user's profile
            current_user = self.get_user_profile(user_id)
            if not current_user:
                return []
            
            # Get all users
            users = db.collection('users').stream()
            matches = []
            
            for user in users:
                other_user = user.to_dict()
                if user.id != user_id and not other_user.get('buddy_connected'):
                    # Calculate interest similarity
                    similarity = self._calculate_similarity(
                        current_user.get('interests', []),
                        other_user.get('interests', [])
                    )
                    
                    # Calculate mood compatibility
                    mood_match = self._check_mood_compatibility(
                        current_user.get('mood_history', []),
                        other_user.get('mood_history', [])
                    )
                    
                    # Combined score
                    match_score = (similarity * 0.7) + (mood_match * 0.3)
                    
                    matches.append({
                        'user_id': user.id,
                        'score': match_score,
                        'interests': other_user.get('interests', [])
                    })
            
            # Sort by match score and return top matches
            matches.sort(key=lambda x: x['score'], reverse=True)
            return matches[:limit]
        except Exception as e:
            st.error(f"Error finding matches: {e}")
            return []

    def _calculate_similarity(self, interests1, interests2):
        """Calculate cosine similarity between interest vectors"""
        # Create a set of all unique interests
        all_interests = list(set(interests1 + interests2))
        
        # Create binary vectors
        vec1 = [1 if i in interests1 else 0 for i in all_interests]
        vec2 = [1 if i in interests2 else 0 for i in all_interests]
        
        # Calculate cosine similarity
        if not vec1 or not vec2:
            return 0
            
        similarity = cosine_similarity(
            [vec1],
            [vec2]
        )[0][0]
        
        return similarity

    def _check_mood_compatibility(self, mood_history1, mood_history2):
        """Check mood compatibility between users"""
        if not mood_history1 or not mood_history2:
            return 0.5  # Neutral if no mood history
            
        # Get most recent moods
        recent_mood1 = mood_history1[-1]['mood'] if mood_history1 else None
        recent_mood2 = mood_history2[-1]['mood'] if mood_history2 else None
        
        if not recent_mood1 or not recent_mood2:
            return 0.5
            
        # Simple mood matching logic
        mood_scores = {
            'Very Positive': 2,
            'Positive': 1,
            'Neutral': 0,
            'Negative': -1,
            'Very Negative': -2
        }
        
        score1 = mood_scores.get(recent_mood1, 0)
        score2 = mood_scores.get(recent_mood2, 0)
        
        # Calculate compatibility (1 for perfect match, 0 for opposite moods)
        diff = abs(score1 - score2)
        max_diff = 4  # Maximum possible difference
        compatibility = 1 - (diff / max_diff)
        
        return compatibility

    def connect_buddies(self, user1_id, user2_id):
        """Connect two users as buddies"""
        if not db:
            return False
            
        try:
            # Update both users
            db.collection('users').document(user1_id).update({
                'buddy_connected': user2_id
            })
            db.collection('users').document(user2_id).update({
                'buddy_connected': user1_id
            })
            
            # Create a chat room
            chat_ref = db.collection('chats').document()
            chat_ref.set({
                'participants': [user1_id, user2_id],
                'created_at': datetime.now(),
                'last_message': None
            })
            
            return True
        except Exception as e:
            st.error(f"Error connecting buddies: {e}")
            return False

    def send_message(self, chat_id, sender_id, content):
        """Send a message in a chat"""
        if not db:
            return False
            
        try:
            message_ref = db.collection('chats').document(chat_id).collection('messages').document()
            message_ref.set({
                'sender_id': sender_id,
                'content': content,
                'timestamp': datetime.now()
            })
            
            # Update last message
            db.collection('chats').document(chat_id).update({
                'last_message': {
                    'content': content,
                    'timestamp': datetime.now()
                }
            })
            
            return True
        except Exception as e:
            st.error(f"Error sending message: {e}")
            return False

    def get_chat_messages(self, chat_id, limit=50):
        """Get messages from a chat"""
        if not db:
            return []
            
        try:
            messages = (
                db.collection('chats')
                .document(chat_id)
                .collection('messages')
                .order_by('timestamp')
                .limit(limit)
                .stream()
            )
            
            return [msg.to_dict() for msg in messages]
        except Exception as e:
            st.error(f"Error retrieving messages: {e}")
            return []

def render_buddy_system():
    st.subheader("🤝 Buddy Connect")
    
    buddy_system = BuddySystem()
    state = st.session_state.buddy_state
    
    if 'user_id' not in st.session_state:
        st.warning("Please log in to use the Buddy Connect feature.")
        return
    
    # Get current user's profile
    current_user = buddy_system.get_user_profile(st.session_state.user_id)
    
    if not current_user:
        st.error("Unable to load user profile.")
        return
    
    # Check if user already has a buddy
    if current_user.get('buddy_connected'):
        buddy_id = current_user['buddy_connected']
        buddy = buddy_system.get_user_profile(buddy_id)
        
        if buddy:
            st.success(f"You're connected with a buddy!")
            
            # Chat interface
            st.subheader("💬 Chat")
            
            # Find or create chat
            chat_query = (
                db.collection('chats')
                .where('participants', 'array_contains', st.session_state.user_id)
                .limit(1)
                .stream()
            )
            
            chat = next(chat_query, None)
            if chat:
                chat_id = chat.id
                
                # Message input
                message = st.text_input("Type your message...")
                if st.button("Send"):
                    if message:
                        if buddy_system.send_message(chat_id, st.session_state.user_id, message):
                            st.rerun()
                
                # Display messages
                messages = buddy_system.get_chat_messages(chat_id)
                for msg in messages:
                    is_self = msg['sender_id'] == st.session_state.user_id
                    
                    with st.container():
                        if is_self:
                            st.markdown(f"""
                            <div style='text-align: right;'>
                                <small>{msg['timestamp'].strftime('%H:%M')}</small><br>
                                <div style='background-color: #1f618d; padding: 10px; border-radius: 10px; display: inline-block;'>
                                    {msg['content']}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style='text-align: left;'>
                                <small>{msg['timestamp'].strftime('%H:%M')}</small><br>
                                <div style='background-color: #2c3e50; padding: 10px; border-radius: 10px; display: inline-block;'>
                                    {msg['content']}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
    else:
        st.info("Let's find you a buddy!")
        
        # Interest selection
        if 'interests' not in current_user:
            st.write("First, let's set up your interests:")
            interests = st.multiselect(
                "Select your interests",
                [
                    "Technology", "Art", "Music", "Sports",
                    "Reading", "Gaming", "Fitness", "Cooking",
                    "Travel", "Movies", "Science", "Writing"
                ],
                max_selections=5
            )
            
            if st.button("Save Interests"):
                db.collection('users').document(st.session_state.user_id).update({
                    'interests': interests
                })
                st.success("Interests saved!")
                st.rerun()
        else:
            # Find matches
            matches = buddy_system.find_matches(st.session_state.user_id)
            
            if matches:
                st.write("Here are some potential buddies:")
                
                for match in matches:
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"Match Score: {match['score']:.2f}")
                            st.write(f"Interests: {', '.join(match['interests'])}")
                        with col2:
                            if st.button("Connect", key=f"connect_{match['user_id']}"):
                                if buddy_system.connect_buddies(
                                    st.session_state.user_id,
                                    match['user_id']
                                ):
                                    st.success("Connected successfully!")
                                    st.rerun()
            else:
                st.info("No matches found at the moment. Check back later!") 