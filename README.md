# MindSpace - Student Mental Health & Productivity Platform

MindSpace is a comprehensive web application designed to support students' mental health and productivity through AI-powered check-ins, task management, peer support, and wellness features.

## Features

- 🤖 AI Mood Check-in Bot
- ✅ Smart Task Manager
- ⏱️ Focus Session Mode
- 👥 Anonymous Peer Forum
- 🤝 Peer Buddy Connect
- 🆘 SOS / Counselor Help

## Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mindspace.git
cd mindspace
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up Firebase:
- Create a new Firebase project
- Download your Firebase service account key
- Rename it to `firebase-key.json` and place it in the project root
- Create a `.env` file with your Firebase and API configurations

5. Run the application:
```bash
streamlit run app.py
```

## Environment Variables (.env)
```
FIREBASE_API_KEY=your_api_key
FIREBASE_AUTH_DOMAIN=your_auth_domain
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_STORAGE_BUCKET=your_storage_bucket
FIREBASE_MESSAGING_SENDER_ID=your_sender_id
FIREBASE_APP_ID=your_app_id
OPENROUTER_API_KEY=your_openrouter_api_key
```

## Project Structure
```
mindspace/
├── app.py                 # Main Streamlit application
├── config.py             # Configuration settings
├── requirements.txt      # Project dependencies
├── firebase-key.json    # Firebase service account key
├── .env                 # Environment variables
└── components/          # UI components
    ├── mood_bot.py     # AI mood check-in logic
    ├── task_manager.py # Task management
    ├── focus_mode.py   # Focus session
    ├── forum.py        # Peer forum
    └── buddy.py        # Buddy connection
```

## Tech Stack

- Frontend: Streamlit
- Backend: Firebase (Firestore + Auth)
- AI: LangChain, TextBlob, Transformers
- Database: Cloud Firestore

## Contributing

This is a hackathon project. Feel free to fork and improve! 