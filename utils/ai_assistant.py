import streamlit as st
import google.generativeai as genai
from db.db_utils import get_project_config, get_connection, row_to_dict

def get_ai_response(user_prompt):
    """Generate AI response with full project context and persistent phase awareness."""
    config = get_project_config()
    conn = get_connection()
    
    # Get current phase (first incomplete phase)
    current_phase_row = conn.execute("""
        SELECT name FROM phases 
        WHERE order_num = (
            SELECT MIN(order_num) FROM phases p 
            WHERE NOT EXISTS (
                SELECT 1 FROM tasks t 
                WHERE t.phase_id = p.id AND t.status = 'completed'
            )
        )
    """).fetchone()
    
    current_phase = current_phase_row['name'] if current_phase_row else "Site Preparation"
    conn.close()

    system_prompt = f"""You are an expert home construction advisor for Brett's "Crowe's Nest Build" — a 2,000 sq ft forever home on 5 acres in Whitwell, TN (Marion County).
Family: Brett (30M - gaming, hunting, fishing, golf), spouse (26F - passionate horse rider), two daughters (3yo + 8mo).
Lifestyle: Heavy daily mud/TN clay, horse tack, fishing/hunting/golf gear, kids bringing in bugs/lizards/frogs. Outdoors-oriented active family.
Key constraints: $450k budget (updated), owner doing electrical materials only, start April 7 2026.
Current phase: {current_phase}.
Septic permit and building permit are approved. Foundation work is in progress this week.
TN weather risks, clay soils, Marion County permits.

Master QOL/Future-Proofing List (always reference these):
- Mudroom with sloped floor/drain/boot bench
- Reinforced gear storage walls + 20A circuits
- Extra exterior 220V/50A circuits, hose bibs
- Laundry upgrades for horse blankets
- Cat6 pre-wires, gaming wall prep
- Kid-height closet features, bunk bed blocking
- Grab-bar blocking, curbless shower, 36" doors
- Full-extension soft-close drawers everywhere
- And every other item from Brett's list.

Answer practically, concisely, with clear next steps, cost-conscious suggestions, and safety warnings."""

    full_prompt = system_prompt + "\n\nUser: " + user_prompt

    if "GEMINI_API_KEY" in st.secrets:
        try:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"🔌 Gemini error: {str(e)}\n\n**Mock fallback:** {user_prompt} – In your current phase ({current_phase}), finish site prep before foundation. Check weather and get the septic permit this week!"
    
    # Pure mock fallback (always works)
    return f"**Mock AI:** Great question for Crowe's Nest! {user_prompt} → Next step: Complete {current_phase.lower()}. Risk: TN spring rain – cover materials."


def ai_chat_interface():
    """Persistent AI chat interface using ai_messages key."""
    st.subheader("🤖 AI Construction Assistant (Gemini 1.5 Flash)")
    st.caption("Ask anything – phase advice, Do’s/Don’ts, risks, next steps, QOL ideas, etc.")

    # Use explicit "ai_messages" key for clear persistence across sessions/pages
    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    # Display chat history
    for message in st.session_state.ai_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    if prompt := st.chat_input("e.g. What are the next steps after foundation?"):
        # Add user message
        st.session_state.ai_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking with construction expertise..."):
                response = get_ai_response(prompt)
            st.markdown(response)

        # Save assistant response
        st.session_state.ai_messages.append({"role": "assistant", "content": response})

    # Optional copy button for last response
    if st.session_state.ai_messages and st.session_state.ai_messages[-1]["role"] == "assistant":
        if st.button("📋 Copy Last Response"):
            st.write(st.session_state.ai_messages[-1]["content"])
            st.success("✅ Copied to clipboard (manual copy if needed)")