import streamlit as st


def apply_mobile_optimizations():
    """iOS PWA-first CSS + meta tag injection via JS.

    Covers: safe-area insets, touch targets ≥44px, no-zoom on input focus,
    compact layout, horizontal-scroll tables, and smooth iOS scrolling.
    """

    # Inject iOS PWA meta tags into <head> via JS (Streamlit can't do this natively)
    st.markdown("""
    <script>
    (function () {
        var tags = [
            ['apple-mobile-web-app-capable',          'yes'],
            ['apple-mobile-web-app-status-bar-style', 'black-translucent'],
            ['apple-mobile-web-app-title',            "Crowe's Nest"],
            ['mobile-web-app-capable',                'yes'],
            ['theme-color',                           '#0f1c12'],
            ['format-detection',                      'telephone=no']
        ];
        tags.forEach(function (t) {
            if (!document.querySelector('meta[name="' + t[0] + '"]')) {
                var m = document.createElement('meta');
                m.name = t[0];
                m.content = t[1];
                document.head.appendChild(m);
            }
        });
        // Extend viewport to cover the notch / home bar
        var vp = document.querySelector('meta[name="viewport"]');
        if (vp) vp.content = 'width=device-width, initial-scale=1.0, viewport-fit=cover';
    })();
    </script>
    """, unsafe_allow_html=True)

    st.markdown("""
    <style>
        /* ── iOS safe-area custom properties ─────────────────────────── */
        :root {
            --sat: env(safe-area-inset-top,    0px);
            --sar: env(safe-area-inset-right,  0px);
            --sab: env(safe-area-inset-bottom, 0px);
            --sal: env(safe-area-inset-left,   0px);
        }

        /* Prevent iOS font-size inflation on orientation change */
        html { -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }

        /* Remove blue tap flash on all elements */
        * { -webkit-tap-highlight-color: rgba(0, 0, 0, 0); }

        /* Smooth momentum scrolling for main content on iOS */
        section[data-testid="stMain"] > div {
            -webkit-overflow-scrolling: touch;
        }

        /* ── Hide Streamlit default nav ───────────────────────────────── */
        [data-testid="stSidebarNav"] { display: none !important; }

        /* ── Mobile styles (≤ 768 px) ────────────────────────────────── */
        @media (max-width: 768px) {

            /* Tight layout respecting notch + home indicator */
            .block-container {
                padding-top:    max(0.75rem, var(--sat)) !important;
                padding-bottom: max(1.5rem,  var(--sab)) !important;
                padding-left:   max(0.5rem,  var(--sal)) !important;
                padding-right:  max(0.5rem,  var(--sar)) !important;
                max-width: 100% !important;
            }

            /* ── Touch-friendly buttons (Apple HIG: min 44 × 44 pt) ──── */
            .stButton > button {
                min-height: 48px !important;
                font-size: 1rem !important;
                padding: 0.6rem 1.2rem !important;
                touch-action: manipulation !important;
                user-select: none !important;
                -webkit-user-select: none !important;
            }

            /* ── Prevent iOS zoom on input focus (font-size must be ≥16px) */
            input, select, textarea,
            [data-testid="stTextInput"] input,
            [data-testid="stNumberInput"] input,
            [data-testid="stDateInput"] input,
            [data-testid="stSelectbox"] div[data-baseweb="select"] input,
            [data-testid="stTextArea"] textarea {
                font-size: 16px !important;
            }

            /* ── Horizontal scroll for wide tables / data editors ──────── */
            .stDataEditor, .stDataFrame,
            [data-testid="stDataFrame"],
            [data-testid="stDataEditor"] {
                overflow-x: auto !important;
                -webkit-overflow-scrolling: touch !important;
            }

            /* ── Headings ───────────────────────────────────────────────── */
            h1 { font-size: 1.45rem !important; margin-bottom: 0.4rem !important; }
            h2 { font-size: 1.2rem  !important; }
            h3 { font-size: 1.05rem !important; }

            /* ── Metrics ────────────────────────────────────────────────── */
            [data-testid="stMetric"] label           { font-size: 0.78rem !important; }
            [data-testid="stMetric"] [data-testid="stMetricValue"] {
                font-size: 1.2rem !important;
            }

            /* ── Charts ─────────────────────────────────────────────────── */
            .stPlotlyChart { margin-bottom: 0.75rem !important; }

            /* ── Sidebar: home-indicator safe area ──────────────────────── */
            [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
                padding-bottom: calc(1rem + var(--sab)) !important;
            }

            /* ── File uploader: compact on mobile ───────────────────────── */
            [data-testid="stFileUploader"] section {
                padding: 0.5rem !important;
            }

            /* ── Expander headers: touch target ─────────────────────────── */
            .streamlit-expanderHeader,
            details > summary {
                min-height: 44px !important;
                display: flex !important;
                align-items: center !important;
            }

            /* ── Tabs: bigger tap area ───────────────────────────────────── */
            [data-testid="stTabs"] button {
                font-size: 0.88rem !important;
                padding: 0.5rem 0.6rem !important;
                min-height: 44px !important;
            }

            /* ── Forms: slight card feel ─────────────────────────────────── */
            [data-testid="stForm"] {
                border-radius: 8px !important;
                padding: 0.75rem !important;
            }

            /* ── Alerts: compact ─────────────────────────────────────────── */
            [data-testid="stAlert"] {
                font-size: 0.9rem !important;
                padding: 0.5rem 0.75rem !important;
            }

            /* ── Camera input: full width ────────────────────────────────── */
            [data-testid="stCameraInput"] { width: 100% !important; }

            /* ── Reduce excess gap between elements ──────────────────────── */
            .element-container { margin-bottom: 0.3rem !important; }

            /* ── Prevent button text selection on long-press ─────────────── */
            button { user-select: none !important; -webkit-user-select: none !important; }
        }
    </style>
    """, unsafe_allow_html=True)
