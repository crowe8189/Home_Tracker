import io
import streamlit as st

try:
    import google.generativeai as genai
    _GENAI_OK = True
except ImportError:
    _GENAI_OK = False

from db.db_utils import get_project_config, get_connection

# Construction photo categories used for AI classification
PHOTO_TAGS = [
    "foundation", "framing", "electrical", "plumbing",
    "drywall", "roofing", "sitework", "exterior",
    "interior_finish", "landscaping", "other",
]


def _get_model():
    """Return a configured Gemini 1.5 Flash model, or None if unavailable."""
    if not _GENAI_OK or "GEMINI_API_KEY" not in st.secrets:
        return None
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    return genai.GenerativeModel("gemini-1.5-flash")


def classify_photo_url(image_url: str):
    """Send a Supabase photo URL to Gemini Vision for construction category classification.

    Returns one of PHOTO_TAGS, or None if classification fails or Gemini is not configured.
    Non-blocking — callers should handle None gracefully.
    """
    model = _get_model()
    if model is None or not image_url or not image_url.startswith("http"):
        return None
    try:
        import urllib.request
        from PIL import Image
        with urllib.request.urlopen(image_url, timeout=12) as resp:
            img = Image.open(io.BytesIO(resp.read()))
        prompt = (
            "You are classifying a home construction site photo. "
            f"Choose exactly one label from this list: {', '.join(PHOTO_TAGS)}. "
            "Reply with only the single label, nothing else."
        )
        response = model.generate_content([prompt, img])
        tag = response.text.strip().lower().rstrip(".")
        return tag if tag in PHOTO_TAGS else "other"
    except Exception:
        return None


def get_ai_response(user_prompt):
    """Generate AI response with full project context."""
    conn = get_connection()
    # fetchone() returns a plain tuple on Turso — use index [0], not key access
    phase_row = conn.execute("""
        SELECT name FROM phases
        WHERE order_num = (
            SELECT MIN(order_num) FROM phases p
            WHERE NOT EXISTS (
                SELECT 1 FROM tasks t
                WHERE t.phase_id = p.id AND t.status = 'completed'
            )
        )
    """).fetchone()
    current_phase = phase_row[0] if phase_row else "Site Preparation"
    conn.close()

    system_prompt = f"""You are an expert home construction advisor for Brett's "Crowe's Nest Build" — a 2,000 sq ft forever home on 5 acres in Whitwell, TN (Marion County).
Family: Brett (30M - gaming, hunting, fishing, golf), spouse (26F - passionate horse rider), two daughters (3yo + 8mo).
Lifestyle: Heavy daily mud/TN clay, horse tack, fishing/hunting/golf gear, kids bringing in bugs/lizards/frogs. Outdoors-oriented active family.
Key constraints: $450k budget, owner doing electrical materials only, start April 7 2026.
Current phase: {current_phase}.
Septic permit and building permit are approved. Foundation work is in progress.
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

Answer practically, concisely, with clear next steps, cost-conscious suggestions, and safety warnings."""

    model = _get_model()
    if model:
        try:
            response = model.generate_content(system_prompt + "\n\nUser: " + user_prompt)
            return response.text
        except Exception as e:
            return (
                f"🔌 Gemini error: {e}\n\n"
                f"**Fallback:** In phase {current_phase} — finish site prep before foundation. "
                "Check weather and confirm permits this week!"
            )

    return (
        f"**Mock AI:** Great question for Crowe's Nest! → Next step: Complete "
        f"{current_phase.lower()}. Risk: TN spring rain – cover materials."
    )


def ai_chat_interface():
    """Persistent AI chat interface."""
    st.subheader("🤖 AI Construction Assistant (Gemini 1.5 Flash)")
    st.caption("Ask anything – phase advice, Do's/Don'ts, risks, next steps, QOL ideas…")

    if "GEMINI_API_KEY" not in st.secrets:
        st.warning(
            "⚠️ GEMINI_API_KEY not set — responses are mock answers. "
            "Add your Gemini API key in Streamlit Cloud → Settings → Secrets."
        )

    if "ai_messages" not in st.session_state:
        st.session_state.ai_messages = []

    for message in st.session_state.ai_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("e.g. What are the next steps after foundation?"):
        st.session_state.ai_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                response = get_ai_response(prompt)
            st.markdown(response)
        st.session_state.ai_messages.append({"role": "assistant", "content": response})

    if st.session_state.ai_messages and st.session_state.ai_messages[-1]["role"] == "assistant":
        if st.button("📋 Copy Last Response"):
            st.write(st.session_state.ai_messages[-1]["content"])
            st.success("✅ Copied (manual copy if needed)")
