from fpdf import FPDF
import plotly.io as pio
from datetime import date
import os
from db.db_utils import get_project_config, get_connection
from utils.charts import create_budget_pie, create_gantt

class ConstructionBinder(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Crowe's Nest Build - Construction Binder", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Generated on {date.today().strftime('%B %d, %Y')} - Page {self.page_no()}", align="C")

def generate_construction_binder():
    """Generates a professional Construction Binder PDF with embedded progress photos"""
    config = get_project_config()
    conn = get_connection()

    pdf = ConstructionBinder()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # === COVER ===
    pdf.set_font("Arial", "B", 22)
    pdf.cell(0, 20, config['name'], ln=True, align="C")
    pdf.set_font("Arial", "", 13)
    pdf.cell(0, 8, config['address'], ln=True, align="C")
    pdf.cell(0, 8, f"Construction Started: {config['start_date']}", ln=True, align="C")
    pdf.cell(0, 8, f"Total Budget: ${config['total_budget']:,.0f}", ln=True, align="C")
    pdf.ln(15)

    # === 1. BUDGET SUMMARY ===
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "1. Budget Summary", ln=True)
    pdf.set_font("Arial", "", 11)
    spent = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()[0]
    remaining = config['total_budget'] - spent
    pdf.cell(0, 8, f"Total Budget      : ${config['total_budget']:,.0f}", ln=True)
    pdf.cell(0, 8, f"Amount Spent      : ${spent:,.0f}", ln=True)
    pdf.cell(0, 8, f"Remaining Budget  : ${remaining:,.0f}", ln=True)
    pdf.ln(8)

    try:
        pie_fig = create_budget_pie()
        pie_img = pio.to_image(pie_fig, format="png", width=700, height=450)
        pdf.image(pie_img, x=15, w=170)
    except:
        pdf.cell(0, 8, "(Budget chart could not be rendered)", ln=True)
    pdf.ln(12)

    # === 2. PROJECT GANTT ===
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "2. Project Gantt", ln=True)
    try:
        gantt_fig = create_gantt()
        gantt_img = pio.to_image(gantt_fig, format="png", width=800, height=650)
        pdf.image(gantt_img, x=10, w=180)
    except:
        pdf.cell(0, 8, "(Gantt chart could not be rendered)", ln=True)
    pdf.ln(15)

    # === 3. TASK PROGRESS BY PHASE ===
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "3. Task Progress by Phase", ln=True)
    pdf.set_font("Arial", "", 10)
    progress_data = conn.execute("""
        SELECT p.name as Phase,
               COUNT(*) as total_tasks,
               SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
        FROM phases p
        LEFT JOIN tasks t ON p.id = t.phase_id
        GROUP BY p.name, p.order_num
        ORDER BY p.order_num
    """).fetchall()

    for row in progress_data:
        completed = row['completed_tasks'] or 0
        total = row['total_tasks'] or 0
        pct = int((completed / total * 100)) if total > 0 else 0
        pdf.cell(0, 8, f"{row['Phase']}: {completed}/{total} tasks complete ({pct}%)", ln=True)
    pdf.ln(10)

    # === 4. KEY PROGRESS PHOTOS (NOW WITH ACTUAL IMAGES) ===
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "4. Key Progress Photos", ln=True)
    pdf.set_font("Arial", "", 10)

    photos = conn.execute("""
        SELECT file_path, original_filename, notes, upload_date
        FROM receipts 
        WHERE file_category = 'photo'
        ORDER BY upload_date DESC 
        LIMIT 6
    """).fetchall()

    for photo in photos:
        pdf.cell(0, 8, f"{photo['upload_date']} - {photo['original_filename']}", ln=True)
        if photo['notes']:
            pdf.cell(0, 6, f"   {photo['notes'][:100]}...", ln=True)

        # Try to embed the actual image
        try:
            if os.path.exists(photo['file_path']) and not str(photo['file_path']).startswith("http"):
                pdf.image(photo['file_path'], x=15, w=120)   # adjust width as needed
                pdf.ln(5)
            else:
                pdf.cell(0, 8, "   (Image file not found)", ln=True)
        except Exception:
            pdf.cell(0, 8, "   (Could not embed image)", ln=True)
        pdf.ln(8)

    # === 5. PERMITS & INSPECTIONS ===
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "5. Permits & Inspections", ln=True)
    pdf.set_font("Arial", "", 11)
    permits = conn.execute("""
        SELECT name, status, required_date, issued_date 
        FROM permits ORDER BY required_date
    """).fetchall()
    
    for p in permits:
        status_text = "APPROVED" if p['status'] == 'approved' or p['issued_date'] else "PENDING"
        pdf.cell(0, 8, f"- {p['name']} - {status_text} ({p['required_date']})", ln=True)

    conn.close()
    pdf.ln(15)

    # Final note
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, "This document was automatically generated by Crowe's Nest Build", align="C")

    # Save
    filename = f"Crowes_Nest_Construction_Binder_{date.today().strftime('%Y%m%d')}.pdf"
    pdf.output(filename)
    return filename