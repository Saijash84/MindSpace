import streamlit as st
from groq import Groq
from datetime import datetime
from services.db_service import DatabaseService
from services.storage_service import StorageService
import time

class MoodBot:
    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self.api_key = st.secrets["GROQ_API_KEY"]
        self.client = Groq(api_key=self.api_key)
        self.model = "llama3-70b-8192"
        
        # Initialize styles
        self.conversation_styles = {
            "Supportive": "You are a supportive and empathetic listener.",
            "Motivational": "You are an encouraging and uplifting coach.",
            "Analytical": "You are a thoughtful and logical guide."
        }

    def get_chat_response(self, user_message: str, mood: str, style: str) -> str:
        """Get AI response with loading indicator"""
        with st.spinner('AI is thinking...'):
            try:
                system_message = self._create_system_message(mood, style)
                messages = self._prepare_messages(system_message, user_message)
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=150
                )
                
                return response.choices[0].message.content
            except Exception as e:
                st.error(f"Error getting AI response: {str(e)}")
                return None

    def _create_system_message(self, mood: str, style: str) -> str:
        return f"""You are a supportive AI companion helping users track and understand their mood.
        Current mood: {mood}
        Style: {self.conversation_styles[style]}
        
        Guidelines:
        1. Never provide medical advice
        2. Encourage professional help when needed
        3. Be empathetic and understanding
        4. Keep responses concise
        5. Use appropriate emojis
        6. Ask thoughtful follow-up questions
        """

    def _prepare_messages(self, system_message: str, user_message: str) -> list:
        messages = [{"role": "system", "content": system_message}]
        
        # Add chat history context
        if 'chat_history' in st.session_state:
            for msg in st.session_state.chat_history[-5:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        messages.append({"role": "user", "content": user_message})
        return messages

    def render_chat_interface(self):
        st.markdown("""
            <style>
                /* Import custom CSS */
                @import url('static/css/style.css');
            </style>
        """, unsafe_allow_html=True)

        # Mood selection
        moods = ["😊 Happy", "😢 Sad", "😡 Angry", "😰 Anxious", "😴 Tired", "😌 Calm"]
        selected_mood = st.radio("How are you feeling today?", moods, horizontal=True)
        mood = selected_mood.split()[1]

        # Style selection
        style = st.selectbox("Choose conversation style", list(self.conversation_styles.keys()))

        # Chat container
        chat_container = st.container()
        
        with chat_container:
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            
            # Display chat history
            for msg in st.session_state.get('chat_history', []):
                css_class = "user-message" if msg["role"] == "user" else "ai-message"
                st.markdown(f"""
                    <div class="chat-message {css_class}">
                        {msg["content"]}
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

        # Input form
        with st.form(key="chat_form", clear_on_submit=True):
            user_message = st.text_input("Type your message...")
            submit_button = st.form_submit_button("Send")
            
            if submit_button and user_message:
                # Get AI response
                ai_response = self.get_chat_response(user_message, mood, style)
                
                if ai_response:
                    # Save to database
                    self.save_chat_entry(user_message, ai_response, mood, style)
                    
                    # Force refresh to show new messages
                    st.rerun()

    def save_chat_entry(self, user_message, ai_response, mood, style):
        """Save chat entry to storage"""
        chat_data = {
            "user_message": user_message,
            "ai_response": ai_response,
            "mood": mood,
            "style": style,
            "timestamp": datetime.now().isoformat()
        }
        
        user_id = st.session_state.get('user_id')
        if user_id:
            self.storage_service.save_mood_entry(user_id, chat_data)
        
        # Update local chat history
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        st.session_state.chat_history.extend([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": ai_response}
        ])

def render_mood_check_in(storage_service: StorageService):
    """Main function to render the mood check-in interface"""
    mood_bot = MoodBot(storage_service)
    mood_bot.render_chat_interface() 