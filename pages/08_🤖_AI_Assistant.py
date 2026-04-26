import streamlit as st

st.set_page_config(page_title="AI Assistant", layout="wide", page_icon="🤖")

from utils.ai_assistant import ai_chat_interface
from utils.sidebar import render_sidebar

render_sidebar()
st.title("🤖 AI Construction Assistant")

if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = []

ai_chat_interface()

st.info("💡 Tip: Ask about sequencing, TN weather risks, permit timing, QOL ideas…")
