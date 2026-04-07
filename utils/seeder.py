from datetime import datetime, timedelta

def seed_data(conn):
    c = conn.cursor()

    # Project config - parameterized to avoid quote issues
    c.execute("""INSERT OR REPLACE INTO project_config 
                 (id, name, total_budget, start_date, address)
                 VALUES (1, ?, ?, ?, ?)""",
              ("Crowe's Nest Build", 350000.0, "2026-04-07", "450 SR 27, Whitwell, TN 37397"))

    # 12 Budget categories
    categories = [
        ("Site Preparation & Dirtwork", 25000, ""),
        ("Foundation & Concrete", 45000, ""),
        ("Framing & Lumber", 80000, ""),
        ("Roofing", 30000, ""),
        ("Electrical – Materials Only", 12000, "Owner Labor – No labor cost tracked"),
        ("Plumbing", 25000, ""),
        ("HVAC & Ductwork", 22000, ""),
        ("Insulation & Drywall", 18000, ""),
        ("Windows & Exterior Doors", 28000, ""),
        ("Interior Finishes (Trim, Paint)", 15000, ""),
        ("Flooring", 22000, ""),
        ("Kitchen & Bath Fixtures", 28000, ""),
    ]
    c.executemany("INSERT OR REPLACE INTO budget_categories (name, planned_amount, notes) VALUES (?,?,?)", categories)

    # 10 Phases
    phases = [
        ("1. Site Preparation", 1, "Dirtwork, clearing, grading – begins today!"),
        ("2. Foundation", 2, "Concrete, footings, slab"),
        ("3. Framing", 3, "Walls, roof trusses"),
        ("4. Rough-ins", 4, "Plumbing, electrical, HVAC"),
        ("5. Roofing", 5, "Shingles, flashing"),
        ("6. Exterior Finishes", 6, "Siding, windows, doors"),
        ("7. Insulation & Drywall", 7, "Insulation, hanging, taping"),
        ("8. Interior Finishes", 8, "Trim, paint, cabinets"),
        ("9. Fixtures & Appliances", 9, "Lighting, plumbing fixtures, appliances"),
        ("10. Landscaping & Punch List", 10, "Final grading, driveway, cleanup"),
    ]
    c.executemany("INSERT OR REPLACE INTO phases (name, order_num, description) VALUES (?,?,?)", phases)

    # 25 realistic tasks (unchanged)
    start = datetime(2026, 4, 7)
    tasks_data = [
        (1, "Clear lot & grade", "Remove trees, level site", start.strftime("%Y-%m-%d"), (start+timedelta(days=5)).strftime("%Y-%m-%d"), (start+timedelta(days=7)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (1, "Install temporary utilities", "", (start+timedelta(days=3)).strftime("%Y-%m-%d"), (start+timedelta(days=10)).strftime("%Y-%m-%d"), (start+timedelta(days=12)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (1, "Erosion control & silt fence", "", (start+timedelta(days=6)).strftime("%Y-%m-%d"), (start+timedelta(days=12)).strftime("%Y-%m-%d"), (start+timedelta(days=14)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (2, "Dig footings", "", (start+timedelta(days=10)).strftime("%Y-%m-%d"), (start+timedelta(days=20)).strftime("%Y-%m-%d"), (start+timedelta(days=22)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (2, "Pour foundation", "", (start+timedelta(days=21)).strftime("%Y-%m-%d"), (start+timedelta(days=28)).strftime("%Y-%m-%d"), (start+timedelta(days=30)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (2, "Cure & backfill", "", (start+timedelta(days=29)).strftime("%Y-%m-%d"), (start+timedelta(days=35)).strftime("%Y-%m-%d"), (start+timedelta(days=37)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (3, "Frame walls & floors", "", (start+timedelta(days=36)).strftime("%Y-%m-%d"), (start+timedelta(days=56)).strftime("%Y-%m-%d"), (start+timedelta(days=58)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (3, "Install roof trusses", "", (start+timedelta(days=57)).strftime("%Y-%m-%d"), (start+timedelta(days=64)).strftime("%Y-%m-%d"), (start+timedelta(days=66)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (3, "Sheathe exterior", "", (start+timedelta(days=65)).strftime("%Y-%m-%d"), (start+timedelta(days=72)).strftime("%Y-%m-%d"), (start+timedelta(days=74)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (4, "Rough plumbing", "", (start+timedelta(days=73)).strftime("%Y-%m-%d"), (start+timedelta(days=82)).strftime("%Y-%m-%d"), (start+timedelta(days=84)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (4, "Rough electrical materials install (owner)", "", (start+timedelta(days=83)).strftime("%Y-%m-%d"), (start+timedelta(days=94)).strftime("%Y-%m-%d"), (start+timedelta(days=96)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (4, "Rough HVAC", "", (start+timedelta(days=95)).strftime("%Y-%m-%d"), (start+timedelta(days=102)).strftime("%Y-%m-%d"), (start+timedelta(days=104)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (5, "Install roofing shingles", "", (start+timedelta(days=103)).strftime("%Y-%m-%d"), (start+timedelta(days=112)).strftime("%Y-%m-%d"), (start+timedelta(days=114)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (5, "Flash chimneys & valleys", "", (start+timedelta(days=113)).strftime("%Y-%m-%d"), (start+timedelta(days=118)).strftime("%Y-%m-%d"), (start+timedelta(days=120)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (6, "Install siding", "", (start+timedelta(days=119)).strftime("%Y-%m-%d"), (start+timedelta(days=131)).strftime("%Y-%m-%d"), (start+timedelta(days=133)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (6, "Install windows & doors", "", (start+timedelta(days=132)).strftime("%Y-%m-%d"), (start+timedelta(days=141)).strftime("%Y-%m-%d"), (start+timedelta(days=143)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (7, "Install insulation", "", (start+timedelta(days=142)).strftime("%Y-%m-%d"), (start+timedelta(days=152)).strftime("%Y-%m-%d"), (start+timedelta(days=154)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (7, "Hang drywall", "", (start+timedelta(days=153)).strftime("%Y-%m-%d"), (start+timedelta(days=165)).strftime("%Y-%m-%d"), (start+timedelta(days=167)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (7, "Tape & mud drywall", "", (start+timedelta(days=166)).strftime("%Y-%m-%d"), (start+timedelta(days=175)).strftime("%Y-%m-%d"), (start+timedelta(days=177)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (8, "Install trim & baseboards", "", (start+timedelta(days=176)).strftime("%Y-%m-%d"), (start+timedelta(days=188)).strftime("%Y-%m-%d"), (start+timedelta(days=190)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (8, "Paint interior", "", (start+timedelta(days=189)).strftime("%Y-%m-%d"), (start+timedelta(days=204)).strftime("%Y-%m-%d"), (start+timedelta(days=206)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (8, "Install cabinets", "", (start+timedelta(days=205)).strftime("%Y-%m-%d"), (start+timedelta(days=214)).strftime("%Y-%m-%d"), (start+timedelta(days=216)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (9, "Install fixtures & lighting", "", (start+timedelta(days=215)).strftime("%Y-%m-%d"), (start+timedelta(days=225)).strftime("%Y-%m-%d"), (start+timedelta(days=227)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (9, "Install appliances", "", (start+timedelta(days=226)).strftime("%Y-%m-%d"), (start+timedelta(days=232)).strftime("%Y-%m-%d"), (start+timedelta(days=234)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (10, "Final grading & driveway", "", (start+timedelta(days=233)).strftime("%Y-%m-%d"), (start+timedelta(days=245)).strftime("%Y-%m-%d"), (start+timedelta(days=247)).strftime("%Y-%m-%d"), "not_started", None, ""),
        (10, "Landscaping & punch list", "", (start+timedelta(days=246)).strftime("%Y-%m-%d"), (start+timedelta(days=275)).strftime("%Y-%m-%d"), (start+timedelta(days=280)).strftime("%Y-%m-%d"), "not_started", None, ""),
    ]
    c.executemany("""INSERT OR REPLACE INTO tasks 
        (phase_id, title, description, planned_start, planned_end, due_date, status, completed_date, notes) 
        VALUES (?,?,?,?,?,?,?,?,?)""", tasks_data)

    # Sample dependencies
    deps = [
        (4, 3), (7, 6), (10, 9), (13, 12), (16, 15),
        (19, 18), (22, 21), (25, 24)
    ]
    c.executemany("INSERT OR REPLACE INTO task_dependencies (task_id, prerequisite_id) VALUES (?,?)", deps)

    # Permits & Inspections
    c.execute("DELETE FROM permits")
    permits_data = [
        ("Septic System Permit", "pending", "2026-04-14", None, "TDEC – must be approved BEFORE building permit. Soil test required first.", None),
        ("County Building Permit", "pending", "2026-04-21", None, "Marion County – requires plans, septic approval, Owner/Builder Agreement", None),
        ("Electrical Permit (State)", "pending", "2026-05-01", None, "SFMO – required before rough electrical", None),
        ("Plumbing Permit", "pending", "2026-05-01", None, "Required before rough plumbing", None),
        ("Mechanical/HVAC Permit", "pending", "2026-05-01", None, "Required before rough HVAC", None),
        ("Footing Inspection", "pending", "2026-04-28", None, "After trenches + rebar. TERMITE TREATMENT REQUIRED FIRST.", None),
        ("Foundation Inspection", "pending", "2026-05-15", None, "After concrete cured + anchor bolts", None),
        ("Rough-In Inspection", "pending", "2026-07-01", None, "After framing + all rough trades. Do NOT insulate yet.", None),
        ("Final Inspection & CO", "pending", "2026-12-01", None, "All work complete + termite record on file", None),
    ]
    c.executemany("""INSERT INTO permits 
        (name, status, required_date, issued_date, notes, document_path) 
        VALUES (?,?,?,?,?,?)""", permits_data)

    conn.commit()
    print("✅ All data seeded successfully on Turso")