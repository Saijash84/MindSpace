import firebase_admin
from firebase_admin import auth, credentials
import jwt
import datetime
import streamlit as st
from typing import Optional, Dict, Any

class AuthService:
    def __init__(self, firebase_config: Dict[str, Any]):
        self.config = firebase_config
        if not firebase_admin._apps:
            cred = credentials.Certificate("firebase-credentials.json")
            firebase_admin.initialize_app(cred)

    def create_user(self, email: str, password: str, display_name: str) -> Dict[str, Any]:
        """Create a new user and send verification email"""
        try:
            user = auth.create_user(
                email=email,
                password=password,
                display_name=display_name,
                email_verified=False
            )
            
            # Generate email verification link
            link = auth.generate_email_verification_link(email)
            
            # TODO: Send verification email using your email service
            
            return {
                "success": True,
                "user": user,
                "verification_link": link
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def verify_email(self, verification_code: str) -> bool:
        """Verify user's email"""
        try:
            # Verify the email verification code
            auth.verify_email_verification_code(verification_code)
            return True
        except Exception:
            return False

    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login user and create session"""
        try:
            user = auth.get_user_by_email(email)
            
            # Check if email is verified
            if not user.email_verified:
                return {
                    "success": False,
                    "error": "Please verify your email before logging in"
                }
            
            # Create session token
            session_token = self._create_session_token(user.uid)
            
            return {
                "success": True,
                "user": user,
                "session_token": session_token
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _create_session_token(self, user_id: str) -> str:
        """Create a JWT session token"""
        expiry = datetime.datetime.now() + datetime.timedelta(days=7)
        payload = {
            "user_id": user_id,
            "exp": expiry
        }
        return jwt.encode(payload, self.config["apiKey"], algorithm="HS256")

    def verify_session(self, session_token: Optional[str]) -> Dict[str, Any]:
        """Verify session token"""
        if not session_token:
            return {"valid": False}
        
        try:
            payload = jwt.decode(session_token, self.config["apiKey"], algorithms=["HS256"])
            user = auth.get_user(payload["user_id"])
            return {
                "valid": True,
                "user": user
            }
        except Exception:
            return {"valid": False}

    def logout_user(self) -> None:
        """Clear user session"""
        if "session_token" in st.session_state:
            del st.session_state.session_token 