import streamlit as st
from utils.ai_assistant import ai_chat_interface
from utils.sidebar import render_sidebar
render_sidebar()
st.set_page_config(page_title="AI Assistant", layout="wide", page_icon="🤖")
st.title("🤖 AI Construction Assistant")

# Persistent history via session_state (survives page reloads)
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []

ai_chat_interface()  # The function already uses st.session_state.messages – we can rename for clarity if you want

st.info("💡 Tip: Ask about sequencing, TN weather risks, permit timing...")