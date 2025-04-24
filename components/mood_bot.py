import streamlit as st
from groq import Groq
import os
from datetime import datetime

class MoodBot:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")
        if not self.api_key:
            st.error("Please set GROQ_API_KEY in your environment variables or Streamlit secrets")
            st.stop()
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama3-70b-8192"
        
        # Style guide
        self.conversation_styles = {
            "Supportive": "Focus on emotional support, gentle reassurance, and active listening.",
            "Motivational": "Be energetic, uplifting, and use goal-oriented encouragement.",
            "Analytical": "Help users explore the reasons behind their feelings with logical clarity."
        }

        # Mood-specific tones
        self.mood_tones = {
            "Happy": "Celebrate the user's joy with positivity and shared excitement. Keep the tone upbeat!",
            "Sad": "Speak gently, offer comfort, and validate their feelings of sadness.",
            "Angry": "Stay calm and supportive, encourage healthy expression and reflection without judgment.",
            "Anxious": "Provide reassurance, breathing space, and stress-relieving suggestions.",
            "Tired": "Acknowledge exhaustion, promote rest and self-care gently.",
            "Calm": "Match their peaceful mood and encourage them to share what’s keeping them grounded."
        }

        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []

    def get_chat_response(self, user_message, mood, style="Supportive"):
        try:
            mood_tone = self.mood_tones.get(mood, "")
            style_instruction = self.conversation_styles.get(style, "")
            
            system_message = f"""
            You are an empathetic AI companion that adapts to the user's emotional state and conversation style.

            Current Mood: {mood}
            Mood Tone Instruction: {mood_tone}
            Style Guide: {style_instruction}

            Guidelines:
            1. Do not give medical or psychiatric advice.
            2. Focus on being a helpful emotional companion.
            3. Ask gentle follow-up questions related to the user's feelings.
            4. Match tone and language to the user's current emotion.
            5. Use brief, empathetic, and human-like responses (with emojis if suitable).
            6. Always validate the user's emotional state first before offering thoughts.
            """

            messages = [
                {"role": "system", "content": system_message},
                *[{"role": msg["role"], "content": msg["content"]} for msg in st.session_state.chat_history[-5:]],
                {"role": "user", "content": user_message}
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=180
            )

            return response.choices[0].message.content

        except Exception as e:
            st.error(f"Error getting AI response: {str(e)}")
            return None

    def save_chat_entry(self, user_message, ai_response, mood, style):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "ai_response": ai_response,
            "mood": mood,
            "style": style
        }
        st.session_state.chat_history.append(entry)

    def render_mood_check_in(self, history):
        st.title("Mood Check-In 🎭")

        moods = ["😊 Happy", "😢 Sad", "😡 Angry", "😰 Anxious", "😴 Tired", "😌 Calm"]
        selected_mood = st.radio("How are you feeling today?", moods, horizontal=True)
        mood = selected_mood.split()[1]  # Extract word after emoji

        style = st.selectbox("Conversation Style", list(self.conversation_styles.keys()))

        st.write("---")
        st.write("### Chat with your AI companion")

        for entry in st.session_state.chat_history:
            st.write(f"**You ({entry['mood']})**: {entry['user_message']}")
            st.write(f"**AI ({entry['style']})**: {entry['ai_response']}")
            st.write("---")

        user_message = st.text_input("Type your message here...")

        if user_message:
            ai_response = self.get_chat_response(user_message, mood, style)

            if ai_response:
                self.save_chat_entry(user_message, ai_response, mood, style)
                history.add_mood_checkin(mood, user_message, ai_response)
                st.rerun()

def render_mood_check_in(history):
    mood_bot = MoodBot()
    mood_bot.render_mood_check_in(history)
