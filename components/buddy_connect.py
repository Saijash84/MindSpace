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

def render_buddy_connect():
    st.subheader("🤝 Buddy Connect")
    
    buddy_connect = BuddyConnect()
    
    if 'user_id' not in st.session_state:
        st.warning("Please log in to use Buddy Connect")
        return
    
    # Profile Management
    with st.expander("My Profile"):
        profile = buddy_connect.get_profile(st.session_state.user_id)
        
        if not profile:
            with st.form("create_profile"):
                name = st.text_input("Name")
                interests = st.multiselect(
                    "Interests",
                    ["Study Groups", "Mental Health", "Career Development", "Hobbies", "Sports"]
                )
                bio = st.text_area("Bio")
                
                if st.form_submit_button("Create Profile"):
                    if name and interests and bio:
                        if buddy_connect.create_profile(
                            st.session_state.user_id,
                            name,
                            interests,
                            bio
                        ):
                            st.success("Profile created successfully!")
                            st.rerun()
                    else:
                        st.warning("Please fill in all fields.")
        else:
            st.write(f"**Name:** {profile['name']}")
            st.write(f"**Interests:** {', '.join(profile['interests'])}")
            st.write(f"**Bio:** {profile['bio']}")
            
            if st.button("Edit Profile"):
                with st.form("edit_profile"):
                    new_name = st.text_input("Name", value=profile['name'])
                    new_interests = st.multiselect(
                        "Interests",
                        ["Study Groups", "Mental Health", "Career Development", "Hobbies", "Sports"],
                        default=profile['interests']
                    )
                    new_bio = st.text_area("Bio", value=profile['bio'])
                    
                    if st.form_submit_button("Update Profile"):
                        if buddy_connect.update_profile(
                            st.session_state.user_id,
                            new_name,
                            new_interests,
                            new_bio
                        ):
                            st.success("Profile updated successfully!")
                            st.rerun()
    
    # Browse Profiles
    st.markdown("---")
    st.subheader("Browse Profiles")
    
    profiles = buddy_connect.get_all_profiles()
    profiles = [p for p in profiles if p['user_id'] != st.session_state.user_id]
    
    if profiles:
        for profile in profiles:
            with st.expander(f"{profile['name']} - {', '.join(profile['interests'])}"):
                st.write(profile['bio'])
                
                # Message Section
                st.markdown("---")
                st.write("💬 Send Message")
                
                with st.form(f"message_form_{profile['user_id']}"):
                    message = st.text_area("Your message")
                    if st.form_submit_button("Send"):
                        if message:
                            if buddy_connect.send_message(
                                st.session_state.user_id,
                                profile['user_id'],
                                message
                            ):
                                st.success("Message sent!")
                                st.rerun()
                        else:
                            st.warning("Please enter a message.")
                
                # View Messages
                messages = buddy_connect.get_messages(st.session_state.user_id, profile['user_id'])
                if messages:
                    st.markdown("---")
                    st.write("📨 Messages")
                    for msg in messages:
                        st.markdown(f"""
                        <div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                            <p>{msg['content']}</p>
                            <small>{'You' if msg['sender_id'] == st.session_state.user_id else profile['name']} | {msg['timestamp']}</small>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.info("No other profiles found yet. Check back later!") 