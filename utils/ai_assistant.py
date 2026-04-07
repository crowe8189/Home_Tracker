import streamlit as st
import google.generativeai as genai
from db.db_utils import get_project_config, get_connection

def get_ai_response(user_prompt):
    config = get_project_config()
    conn = get_connection()
    current_phase_row = conn.execute("""
        SELECT name FROM phases 
        WHERE order_num = (SELECT MIN(order_num) FROM phases p 
                           WHERE NOT EXISTS (SELECT 1 FROM tasks t WHERE t.phase_id = p.id AND t.status = 'completed'))
    """).fetchone()
    current_phase = current_phase_row['name'] if current_phase_row else "Site Preparation"
    conn.close()

    system_prompt = f"""You are an expert home construction advisor for "Crowe's Nest Build" ($350k budget, Whitwell TN, owner doing electrical materials only).
Current phase: {current_phase}. Address: 450 SR 27, Whitwell, TN 37397.
Septic permit is pending. Warn about TN weather, sequencing, permits, and safety.
Answer concisely, practically, and with clear next steps."""

    full_prompt = system_prompt + "\n\nUser: " + user_prompt

    if "GEMINI_API_KEY" in st.secrets:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"🔌 Gemini error: {str(e)}\n\n**Mock fallback:** {user_prompt} – In your current phase, finish site prep before foundation. Check weather and get the septic permit this week!"
    # Pure mock fallback (always works)
    return f"**Mock AI:** Great question for Crowe's Nest! {user_prompt} → Next step: Complete {current_phase.lower()}. Risk: TN spring rain – cover materials."

def ai_chat_interface():
    st.subheader("🤖 AI Assistant (Gemini 1.5 Flash)")
    st.caption("Ask anything – phase advice, Do’s/Don’ts, risks, next steps.")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    if prompt := st.chat_input("e.g. What are the next steps after foundation?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking with construction expertise..."):
                response = get_ai_response(prompt)
            st.markdown(response)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        if st.button("📋 Copy Last Response"):
            st.write(st.session_state.messages[-1]["content"])  # or use st.clipboard
            st.success("Copied to clipboard (manual copy if needed)")
        st.session_state.messages.append({"role": "assistant", "content": response})