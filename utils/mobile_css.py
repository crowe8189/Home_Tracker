import streamlit as st

def apply_mobile_optimizations():
    """Global mobile/PWA improvements – tighter spacing, better scrolling, smaller fonts"""
    st.markdown("""
    <style>
        @media (max-width: 768px) {
            .block-container {
                padding-top: 0.5rem !important;
                padding-bottom: 0.5rem !important;
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
            }
            
            /* Make data editors & tables scroll horizontally on phones */
            .stDataEditor, .stDataFrame, .stTable {
                overflow-x: auto !important;
            }
            
            /* Smaller headings and metrics on mobile */
            h1 { font-size: 1.65rem !important; }
            h2 { font-size: 1.4rem !important; }
            .stMetric { font-size: 0.95rem !important; }
            
            /* Gantt & Plotly charts get better proportions */
            .stPlotlyChart {
                margin-bottom: 1rem !important;
            }
            
            /* Sidebar navigation looks cleaner */
            .stSidebar .stRadio, .stSidebar .stSelectbox {
                font-size: 0.95rem !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)