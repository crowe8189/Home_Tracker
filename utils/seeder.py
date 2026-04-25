from datetime import datetime, timedelta

def seed_data(conn):
    c = conn.cursor()

    # === PROJECT CONFIG ===
    c.execute("""INSERT OR REPLACE INTO project_config 
                 (id, name, total_budget, start_date, address)
                 VALUES (1, ?, ?, ?, ?)""",
              ("Crowe's Nest Build", 450000.0, "2026-04-07", "450 SR 27, Whitwell, TN 37397"))

    # === BUDGET CATEGORIES ($450k - Site Prep already paid separately) ===
    categories = [
        ("Site Preparation & Dirtwork", 0, "Already paid separately - not in $450k house budget"),
        ("Foundation & Concrete (Block)", 65000, "Block foundation + concrete garage/porches"),
        ("Framing & Lumber", 115000, ""),
        ("Roofing", 38000, ""),
        ("Electrical – Materials Only", 18000, "Owner Labor – No labor cost tracked"),
        ("Plumbing", 32000, ""),
        ("HVAC & Ductwork", 28000, ""),
        ("Insulation & Drywall", 22000, ""),
        ("Windows & Exterior Doors", 35000, ""),
        ("Interior Finishes (Trim, Paint)", 22000, ""),
        ("Flooring", 28000, ""),
        ("Kitchen & Bath Fixtures", 37000, ""),
    ]
    c.executemany("INSERT OR REPLACE INTO budget_categories (name, planned_amount, notes) VALUES (?,?,?)", categories)

    # === PHASES ===
    phases = [
        ("1. Site Preparation", 1, "Dirtwork, clearing, grading – completed"),
        ("2. Foundation", 2, "Block foundation + concrete garage/porches"),
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

    # === SIMPLIFIED TASKS WITH CURRENT PROGRESS (as of April 22, 2026) ===
    start = datetime(2026, 4, 7)
    tasks_data = [
        # Site Preparation - Completed
        (1, "Clear lot, grade, and install erosion control", "", "2026-04-07", "2026-04-17", "2026-04-18", "completed", "2026-04-18", ""),
        (1, "Install temporary utilities and silt fence", "", "2026-04-10", "2026-04-19", "2026-04-20", "completed", "2026-04-19", ""),

        # Foundation - In progress this week
        (2, "Dig footings, install rebar and termite treatment", "", "2026-04-20", "2026-04-25", "2026-04-28", "completed", "2026-04-21", ""),
        (2, "Pour block foundation + concrete garage/porches", "", "2026-04-22", "2026-05-05", "2026-05-10", "in_progress", None, "Footers/blocks being poured this week"),

        # Remaining tasks
        (3, "Frame walls, floors, and install roof trusses", "", "2026-05-01", "2026-05-31", "2026-06-05", "not_started", None, ""),
        (3, "Sheathe exterior walls and install house wrap", "", "2026-05-25", "2026-06-10", "2026-06-15", "not_started", None, ""),
        (4, "Rough plumbing, electrical materials (owner), and HVAC", "", "2026-06-01", "2026-06-30", "2026-07-05", "not_started", None, ""),
        (5, "Install roofing, underlayment, shingles, and flashing", "", "2026-07-01", "2026-07-20", "2026-07-25", "not_started", None, ""),
        (6, "Install siding, windows, exterior doors, and gutters", "", "2026-07-20", "2026-08-15", "2026-08-20", "not_started", None, ""),
        (7, "Install insulation and hang/tape/mud drywall", "", "2026-08-01", "2026-09-01", "2026-09-05", "not_started", None, ""),
        (8, "Install trim, paint, cabinets, and interior doors", "", "2026-09-01", "2026-10-01", "2026-10-05", "not_started", None, ""),
        (9, "Install fixtures, lighting, appliances, and trim-out", "", "2026-10-01", "2026-10-25", "2026-10-30", "not_started", None, ""),
        (10, "Final grading, driveway, landscaping, and punch list", "", "2026-11-01", "2026-12-15", "2026-12-20", "not_started", None, ""),
    ]
    c.executemany("""INSERT OR REPLACE INTO tasks 
        (phase_id, title, description, planned_start, planned_end, due_date, status, completed_date, notes) 
        VALUES (?,?,?,?,?,?,?,?,?)""", tasks_data)

    # Dependencies
    deps = [(5, 4), (7, 6), (9, 8), (11, 10)]
    c.executemany("INSERT OR REPLACE INTO task_dependencies (task_id, prerequisite_id) VALUES (?,?)", deps)

    # === QOL Ideas ===
    qol_data = [
        ("Mudroom/Adventure Entry", "Sloped concrete floor + drain, boot bench, cubbies, wall hooks, deep utility sink", 1500, "planned", 1, None, "Critical for daily mud/horse tack/kid treasures"),
        ("Gear Storage", "Reinforced plywood-backed walls for fishing rods, guns, golf clubs", 800, "planned", 1, None, "Owner install"),
        ("Exterior Utilities", "Extra frost-proof hose bibs + 220V/50A circuits to patio/garage/barn", 2500, "planned", 1, None, "Future-proofing"),
        ("Laundry Upgrades", "Extra-deep utility sink + overhead drying rod for horse blankets", 600, "planned", None, None, ""),
        ("Electrical Pre-wires", "Cat6 everywhere + media panel, gaming wall prep", 1200, "planned", 4, None, "Owner labor - materials only"),
        ("Kid-Friendly Closets", "Blocking for bunk/loft beds, second hanging rod + shelf tower at kid height", 400, "planned", None, None, ""),
        ("Bathroom Future-Proofing", "Grab-bar blocking, curbless master shower, 36″ doorways", 1800, "planned", None, None, ""),
        ("Kitchen Convenience", "Full-extension soft-close drawer bases in ALL lower cabinets", 900, "planned", None, None, ""),
    ]
    c.executemany("""INSERT OR REPLACE INTO qol_ideas 
        (category, description, estimated_cost, status, linked_phase_id, linked_task_id, notes)
        VALUES (?,?,?,?,?,?,?)""", qol_data)

    # === PERMITS (Septic + County Building Permit approved) ===
    c.execute("DELETE FROM permits")
    permits_data = [
        ("Septic System Permit", "approved", "2026-04-14", "2026-04-15", "TDEC approved – soil test passed", None),
        ("County Building Permit", "approved", "2026-04-21", "2026-04-20", "Marion County approved – Owner/Builder Agreement on file", None),
        ("Electrical Permit (State)", "pending", "2026-05-01", None, "SFMO – required before rough electrical", None),
        ("Plumbing Permit", "pending", "2026-05-01", None, "Required before rough plumbing", None),
        ("Mechanical/HVAC Permit", "pending", "2026-05-01", None, "Required before rough HVAC", None),
        ("Footing Inspection", "pending", "2026-04-28", None, "After trenches + rebar. TERMITE TREATMENT REQUIRED FIRST.", None),
        ("Foundation Inspection", "pending", "2026-05-15", None, "After concrete cured + anchor bolts", None),
        ("Rough-In Inspection", "pending", "2026-07-01", None, "After framing + all rough trades.", None),
        ("Final Inspection & CO", "pending", "2026-12-01", None, "All work complete + termite record on file", None),
    ]
    c.executemany("""INSERT INTO permits 
        (name, status, required_date, issued_date, notes, document_path) 
        VALUES (?,?,?,?,?,?)""", permits_data)

    conn.commit()
    print("✅ Crowe's Nest Build seeded with $450k budget, current progress, and block foundation!")