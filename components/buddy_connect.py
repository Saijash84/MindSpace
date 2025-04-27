import streamlit as st
from datetime import datetime

class BuddyConnect:
    def __init__(self):
        if 'profiles' not in st.session_state:
            st.session_state.profiles = {}
        if 'connections' not in st.session_state:
            st.session_state.connections = {}
        if 'messages' not in st.session_state:
            st.session_state.messages = {}

    def create_profile(self, user_id, name, interests, bio):
        """Create a new user profile in session state"""
        try:
            profile = {
                'user_id': user_id,
                'name': name,
                'interests': interests,
                'bio': bio,
                'created_at': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            }
            st.session_state.profiles[user_id] = profile
            st.session_state.connections[user_id] = []
            st.session_state.messages[user_id] = {}
            return True
        except Exception as e:
            st.error(f"Error creating profile: {e}")
            return False

    def get_profile(self, user_id):
        """Get user profile from session state"""
        try:
            return st.session_state.profiles.get(user_id)
        except Exception as e:
            st.error(f"Error retrieving profile: {e}")
            return None

    def update_profile(self, user_id, name=None, interests=None, bio=None):
        """Update user profile in session state"""
        try:
            if user_id in st.session_state.profiles:
                profile = st.session_state.profiles[user_id]
                if name:
                    profile['name'] = name
                if interests:
                    profile['interests'] = interests
                if bio:
                    profile['bio'] = bio
                profile['last_active'] = datetime.now().isoformat()
                return True
            return False
        except Exception as e:
            st.error(f"Error updating profile: {e}")
            return False

    def get_all_profiles(self):
        """Get all profiles from session state"""
        try:
            return list(st.session_state.profiles.values())
        except Exception as e:
            st.error(f"Error retrieving profiles: {e}")
            return []

    def send_message(self, sender_id, receiver_id, content):
        """Send a message between users in session state"""
        try:
            if sender_id not in st.session_state.messages:
                st.session_state.messages[sender_id] = {}
            if receiver_id not in st.session_state.messages[sender_id]:
                st.session_state.messages[sender_id][receiver_id] = []
            
            message = {
                'id': str(len(st.session_state.messages[sender_id][receiver_id]) + 1),
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'content': content,
                'timestamp': datetime.now().isoformat(),
                'read': False
            }
            
            st.session_state.messages[sender_id][receiver_id].append(message)
            return True
        except Exception as e:
            st.error(f"Error sending message: {e}")
            return False

    def get_messages(self, user_id, other_user_id):
        """Get messages between two users from session state"""
        try:
            messages = []
            if user_id in st.session_state.messages and other_user_id in st.session_state.messages[user_id]:
                messages.extend(st.session_state.messages[user_id][other_user_id])
            if other_user_id in st.session_state.messages and user_id in st.session_state.messages[other_user_id]:
                messages.extend(st.session_state.messages[other_user_id][user_id])
            return sorted(messages, key=lambda x: x['timestamp'])
        except Exception as e:
            st.error(f"Error retrieving messages: {e}")
            return []

def render_buddy_connect(storage_service, user_id):
    st.header("🤝 Buddy Connect")

    # Edit profile
    profile = storage_service.get_user_profile(user_id)
    with st.form("edit_profile"):
        bio = st.text_area("Your Bio", value=profile.get("bio", ""))
        interests = st.text_input("Your Interests (comma separated)", value=", ".join(profile.get("interests", [])))
        submitted = st.form_submit_button("Update Profile")
        if submitted:
            interests_list = [i.strip() for i in interests.split(",") if i.strip()]
            storage_service.update_user_profile(user_id, bio, interests_list)
            st.success("Profile updated!")

    # Find buddies
    st.subheader("Find Buddies")
    if profile.get("interests"):
        buddies = storage_service.find_buddies_by_interest(user_id, profile["interests"])
        for buddy in buddies:
            st.write(f"**{buddy['name']}** - {buddy['bio']}")
            st.write(f"Interests: {', '.join(buddy['interests'])}")
            if st.button(f"Chat with {buddy['name']}", key=buddy['user_id']):
                chat_id = storage_service.get_or_create_chat(user_id, buddy['user_id'])
                render_buddy_chat(storage_service, chat_id, user_id)
    else:
        st.info("Add interests to find buddies.")

def render_buddy_chat(storage_service, chat_id, user_id):
    st.subheader("Chat")
    messages = storage_service.get_buddy_messages(chat_id)
    for msg in messages:
        st.write(f"{msg['sender']}: {msg['content']} ({msg['type']})")
    # Text message
    text = st.text_input("Type a message")
    if st.button("Send Text"):
        storage_service.send_buddy_message(chat_id, user_id, "text", text)
        st.rerun()
    # Audio/file upload (for brevity, just show upload)
    uploaded_file = st.file_uploader("Send a file or audio", type=["mp3", "wav", "png", "jpg", "pdf"])
    if uploaded_file:
        # You would need to upload this to a storage bucket and save the URL in Firestore
        st.info("File upload handling not implemented in this snippet.") 