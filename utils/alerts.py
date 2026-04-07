from db.db_utils import get_connection
from datetime import date, timedelta

def get_all_alerts():
    alerts = []
    conn = get_connection()
    today = date.today()
    two_weeks = (today + timedelta(days=14)).strftime("%Y-%m-%d")

    # Summary: Permits due soon (only within 2 weeks)
    due_soon_permits = conn.execute("""
        SELECT COUNT(*) as cnt FROM permits 
        WHERE status = 'pending' AND required_date <= ?
    """, (two_weeks,)).fetchone()[0]

    if due_soon_permits > 0:
        alerts.append({
            "level": "info",
            "message": f"📋 {due_soon_permits} permit(s) due soon (within 2 weeks)"
        })

    # Summary: Tasks due soon / overdue
    due_tasks = conn.execute("""
        SELECT COUNT(*) as cnt FROM tasks 
        WHERE status != 'completed' AND due_date <= ?
    """, (two_weeks,)).fetchone()[0]

    if due_tasks > 0:
        alerts.append({
            "level": "info",
            "message": f"🛠️ {due_tasks} task(s) due soon (within 2 weeks)"
        })

    conn.close()
    return alerts