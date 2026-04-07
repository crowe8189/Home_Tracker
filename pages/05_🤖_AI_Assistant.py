import streamlit as st
from utils.ai_assistant import ai_chat_interface

st.set_page_config(page_title="AI Assistant", layout="wide", page_icon="🤖")

st.title("🤖 AI Construction Assistant")
st.caption("Powered by Gemini 1.5 Flash • Phase-aware • Risk warnings • Do’s & Don’ts for Crowe's Nest Build")

# The full chat interface (including history, system prompt with your project data, and mock fallback) is in utils/ai_assistant.py
ai_chat_interface()

st.info("💡 Tip: Ask about sequencing, TN weather risks, permit timing, or next steps after rough-ins. Your Gemini key is used automatically if present in .streamlit/secrets.toml.")