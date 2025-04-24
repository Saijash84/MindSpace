import streamlit as st
from groq import Groq
import os
from datetime import datetime
import json

class StoryGenerator:
    def __init__(self):
        # Try to get API key from environment variable first
        api_key = os.getenv("GROQ_API_KEY")
        
        # If not in environment, try secrets
        if not api_key and "GROQ_API_KEY" in st.secrets:
            api_key = st.secrets["GROQ_API_KEY"]
            
        if not api_key:
            st.error("""
            Groq API key not found. Please set it up in one of these ways:
            
            1. Set as environment variable:
               - Windows: `set GROQ_API_KEY=your-key-here`
               - Linux/Mac: `export GROQ_API_KEY=your-key-here`
            
            2. Or add to secrets.toml:
               ```
               GROQ_API_KEY = "your-key-here"
               ```
            
            Get your API key from https://console.groq.com/
            """)
            return
            
        try:
            self.client = Groq(api_key=api_key)
            self.model = "llama3-70b-8192"  # Using the latest recommended model
        except Exception as e:
            st.error(f"Error initializing Groq client: {e}")
            return

    def generate_story(self, mood, theme):
        try:
            system_message = """You are a creative storyteller who creates inspiring and motivational stories for students.
            - Create engaging narratives that resonate with young readers
            - Include vivid descriptions and emotional depth
            - Ensure the story has a clear moral or lesson
            - Keep the language accessible and relatable
            - Make the story uplifting and hopeful
            - Include specific details that bring the story to life
            - End with a meaningful conclusion that ties everything together
            - Add motivational quotes or lessons
            - Include relatable characters and situations
            - Focus on personal growth and learning
            - Provide actionable insights
            - Use positive and encouraging language"""
            
            prompt = f"""Create an inspirational story for students that:
            1. Matches the mood: {mood}
            2. Focuses on the theme: {theme}
            3. Is uplifting and motivational
            4. Is 3-4 paragraphs long
            5. Has a clear moral or lesson
            6. Includes relatable characters
            7. Provides actionable insights
            8. Ends with a motivational message
            
            Make the story engaging and relatable to students. Include specific examples and situations they might encounter."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=800,
                presence_penalty=0.6,
                frequency_penalty=0.6
            )

            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Error generating story: {e}")
            return None

def render_story_generator():
    st.subheader("📖 Story Generator")
    
    story_generator = StoryGenerator()
    
    # Theme selection with descriptions
    themes = {
        "Perseverance": "Overcoming challenges and never giving up",
        "Kindness": "Acts of compassion and their impact",
        "Courage": "Facing fears and finding strength",
        "Hope": "Finding light in difficult times",
        "Friendship": "The power of connection and support",
        "Growth": "Personal development and learning",
        "Resilience": "Bouncing back from adversity",
        "Gratitude": "Appreciating life's blessings",
        "Confidence": "Believing in yourself and your abilities",
        "Teamwork": "Working together to achieve goals",
        "Creativity": "Thinking outside the box",
        "Responsibility": "Taking ownership of your actions"
    }
    
    selected_theme = st.selectbox(
        "Select a theme for your story",
        options=list(themes.keys()),
        format_func=lambda x: f"{x} - {themes[x]}"
    )
    
    # Mood input with suggestions
    mood = st.text_input(
        "How are you feeling today?",
        placeholder="e.g., hopeful, determined, reflective"
    )
    
    # Additional preferences
    col1, col2 = st.columns(2)
    with col1:
        story_length = st.selectbox(
            "Story Length",
            ["Short (2-3 paragraphs)", "Medium (3-4 paragraphs)", "Long (4-5 paragraphs)"]
        )
    with col2:
        include_quotes = st.checkbox("Include motivational quotes", value=True)
    
    if st.button("Generate Story"):
        if mood:
            with st.spinner("Creating your inspirational story..."):
                story = story_generator.generate_story(mood, selected_theme)
                if story:
                    st.write("---")
                    st.write(story)
                    
                    # Save to session state
                    if 'stories' not in st.session_state:
                        st.session_state.stories = []
                    st.session_state.stories.append({
                        'theme': selected_theme,
                        'mood': mood,
                        'story': story,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    
                    if st.button("Generate Another Story"):
                        st.rerun()
        else:
            st.warning("Please enter your mood to generate a story.")
            
    # Display saved stories
    if 'stories' in st.session_state and st.session_state.stories:
        st.write("---")
        st.subheader("📚 Your Story Collection")
        for story in reversed(st.session_state.stories):
            with st.expander(f"{story['theme']} - {story['mood']} ({story['timestamp']})"):
                st.write(story['story']) 