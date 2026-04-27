def seed_data(conn):
    c = conn.cursor()

    # === PROJECT CONFIG ===
    c.execute("""INSERT OR REPLACE INTO project_config
                 (id, name, total_budget, start_date, address)
                 VALUES (1, ?, ?, ?, ?)""",
              ("Crowe's Nest Build", 450000.0, "2026-04-07", "450 SR 27, Whitwell, TN 37397"))

    # === BUDGET CATEGORIES (sums to $450k) ===
    categories = [
        ("Site Preparation & Dirtwork",                0,      "Paid separately — not in $450k house budget"),
        ("Foundation & Concrete",                      60000,  "Block foundation + concrete garage/porches"),
        ("Framing & Lumber",                           110000, ""),
        ("Roofing",                                    38000,  ""),
        ("Electrical",                                 25000,  "Full labor + materials"),
        ("Plumbing",                                   32000,  ""),
        ("HVAC & Ductwork",                            28000,  ""),
        ("Insulation & Drywall",                       22000,  ""),
        ("Windows & Exterior Doors",                   30000,  ""),
        ("Interior Finishes (Cabinets, Trim & Paint)", 22000,  ""),
        ("Flooring",                                   28000,  ""),
        ("Fixtures, Countertops & Appliances",         37000,  ""),
        ("Siding & Exterior Cladding",                 18000,  ""),
    ]
    c.executemany(
        "INSERT OR REPLACE INTO budget_categories (name, planned_amount, notes) VALUES (?,?,?)",
        categories,
    )

    # === PHASES ===
    phases = [
        ("1. Site Preparation",          1,  "Clearing, grading, temporary utilities"),
        ("2. Foundation",                2,  "Footings, block foundation, concrete slabs"),
        ("3. Framing",                   3,  "Walls, roof trusses, sheathing"),
        ("4. Rough-ins",                 4,  "Plumbing, electrical, HVAC"),
        ("5. Roofing",                   5,  "Underlayment, shingles, flashing"),
        ("6. Exterior Finishes",         6,  "Siding, windows, doors, gutters"),
        ("7. Insulation & Drywall",      7,  "Insulation, hang, tape, mud"),
        ("8. Interior Finishes",         8,  "Cabinets, countertops, tile, flooring, trim, paint"),
        ("9. Fixtures & Appliances",     9,  "Lighting, plumbing fixtures, appliances"),
        ("10. Landscaping & Punch List", 10, "Final grading, driveway, cleanup"),
    ]
    c.executemany(
        "INSERT OR REPLACE INTO phases (name, order_num, description) VALUES (?,?,?)",
        phases,
    )

    # === TASKS ===
    # (phase_id, title, description, planned_start, planned_end, due_date, status, completed_date, notes)
    tasks_data = [
        # ── Site Preparation (phase 1) — completed ─────────────────────────
        (1, "Complete site clearing, grading, erosion control, and temporary utilities",
         "", "2026-04-07", "2026-04-17", "2026-04-18", "completed", "2026-04-17", ""),
        (1, "Install temporary power, water, and portapotty",
         "", "2026-04-10", "2026-04-19", "2026-04-20", "completed", "2026-04-19", ""),

        # ── Foundation (phase 2) ───────────────────────────────────────────
        (2, "Dig footings, install rebar, and termite treatment",
         "", "2026-04-20", "2026-04-21", "2026-04-22", "completed", "2026-04-21", ""),
        (2, "Pour block foundation",
         "", "2026-04-22", "2026-04-24", "2026-04-25", "completed", "2026-04-24", ""),
        (2, "Pour garage concrete slab",
         "", "2026-04-25", "2026-04-26", "2026-04-27", "completed", "2026-04-26", ""),
        (2, "Pour porch concrete",
         "", "2026-04-26", "2026-04-27", "2026-04-28", "completed", "2026-04-27", ""),
        (2, "Waterproof block foundation (backside)",
         "", "2026-04-28", "2026-05-05", "2026-05-10", "not_started", None, ""),

        # ── Framing (phase 3) ─────────────────────────────────────────────
        (3, "Complete structural framing and roof trusses",
         "", "2026-05-01", "2026-06-15", "2026-06-20", "not_started", None, ""),

        # ── Rough-ins (phase 4) ───────────────────────────────────────────
        (4, "Rough plumbing",
         "", "2026-06-15", "2026-07-01", "2026-07-05", "not_started", None, ""),
        (4, "Rough electrical",
         "", "2026-06-20", "2026-07-15", "2026-07-20", "not_started", None, ""),
        (4, "Rough HVAC",
         "", "2026-06-25", "2026-07-31", "2026-08-05", "not_started", None, ""),

        # ── Roofing (phase 5) ─────────────────────────────────────────────
        (5, "Install roofing, underlayment, shingles, and flashing",
         "", "2026-07-15", "2026-08-15", "2026-08-20", "not_started", None, ""),

        # ── Exterior Finishes (phase 6) ───────────────────────────────────
        (6, "Install siding",
         "", "2026-08-15", "2026-09-01", "2026-09-05", "not_started", None, ""),
        (6, "Install windows, exterior doors, and gutters",
         "", "2026-08-20", "2026-09-15", "2026-09-20", "not_started", None, ""),

        # ── Insulation & Drywall (phase 7) ────────────────────────────────
        (7, "Install insulation and hang/tape drywall",
         "", "2026-09-15", "2026-10-15", "2026-10-20", "not_started", None, ""),

        # ── Interior Finishes (phase 8) ───────────────────────────────────
        (8, "Install cabinets and interior doors",
         "", "2026-10-15", "2026-10-25", "2026-10-30", "not_started", None, ""),
        (8, "Install countertops",
         "", "2026-10-25", "2026-11-01", "2026-11-05", "not_started", None, ""),
        (8, "Tile showers and bathrooms",
         "", "2026-10-20", "2026-11-05", "2026-11-10", "not_started", None, ""),
        (8, "Install flooring",
         "", "2026-11-01", "2026-11-15", "2026-11-20", "not_started", None, ""),
        (8, "Install trim",
         "", "2026-11-10", "2026-11-20", "2026-11-25", "not_started", None, ""),
        (8, "Paint",
         "", "2026-11-15", "2026-11-30", "2026-12-05", "not_started", None, ""),

        # ── Fixtures & Appliances (phase 9) ───────────────────────────────
        (9, "Install fixtures, lighting, and appliances",
         "", "2026-11-15", "2026-12-01", "2026-12-05", "not_started", None, ""),

        # ── Landscaping & Punch List (phase 10) ───────────────────────────
        (10, "Final grading, driveway, landscaping, and punch list",
         "", "2026-12-01", "2026-12-20", "2026-12-31", "not_started", None, ""),
    ]
    c.executemany("""INSERT OR REPLACE INTO tasks
        (phase_id, title, description, planned_start, planned_end, due_date,
         status, completed_date, notes)
        VALUES (?,?,?,?,?,?,?,?,?)""", tasks_data)

    # Task IDs 1–23 auto-assigned in insert order above.
    # Sequential cross-phase dependencies + Interior Finishes ordering.
    deps = [
        (8,  7),   # Framing after foundation waterproofing
        (12, 8),   # Roofing after framing
        (15, 8),   # Insulation/drywall after framing
        (16, 15),  # Cabinets after insulation/drywall
        (17, 16),  # Countertops after cabinets
        (20, 19),  # Trim after flooring
        (21, 20),  # Paint after trim
        (22, 21),  # Fixtures after paint
        (23, 22),  # Landscaping after fixtures
    ]
    c.executemany(
        "INSERT OR REPLACE INTO task_dependencies (task_id, prerequisite_id) VALUES (?,?)",
        deps,
    )

    # === QOL IDEAS ===
    qol_data = [
        ("Mudroom / Adventure Entry",
         "Sloped concrete floor + drain, boot bench, cubbies, wall hooks, deep utility sink",
         1500, "planned", 1, None, "Critical for daily mud/horse tack/kid treasures"),
        ("Gear Storage",
         "Reinforced plywood-backed walls for fishing rods, guns, golf clubs",
         800, "planned", 1, None, "Owner install"),
        ("Exterior Utilities",
         "Extra frost-proof hose bibs + 220V/50A circuits to patio/garage/barn",
         2500, "planned", 1, None, "Future-proofing"),
        ("Laundry Upgrades",
         "Extra-deep utility sink + overhead drying rod for horse blankets",
         600, "planned", None, None, ""),
        ("Electrical Pre-wires",
         "Cat6 everywhere + media panel, gaming wall prep",
         1200, "planned", 4, None, ""),
        ("Kid-Friendly Closets",
         "Blocking for bunk/loft beds, second hanging rod + shelf tower at kid height",
         400, "planned", None, None, ""),
        ("Bathroom Future-Proofing",
         "Grab-bar blocking, curbless master shower, 36\" doorways",
         1800, "planned", None, None, ""),
        ("Kitchen Convenience",
         "Full-extension soft-close drawer bases in ALL lower cabinets",
         900, "planned", None, None, ""),
    ]
    c.executemany("""INSERT OR REPLACE INTO qol_ideas
        (category, description, estimated_cost, status, linked_phase_id, linked_task_id, notes)
        VALUES (?,?,?,?,?,?,?)""", qol_data)

    # === PERMITS ===
    c.execute("DELETE FROM permits")
    permits_data = [
        ("Septic System Permit",      "approved", "2026-04-14", "2026-04-15",
         "TDEC approved — soil test passed", None),
        ("County Building Permit",    "approved", "2026-04-21", "2026-04-20",
         "Marion County approved — Owner/Builder Agreement on file", None),
        ("Footing Inspection",        "approved", "2026-04-21", "2026-04-21",
         "Passed — termite treatment completed first", None),
        ("Foundation Inspection",     "approved", "2026-04-27", "2026-04-27",
         "Passed — concrete cured, anchor bolts set", None),
        ("Electrical Permit (State)", "pending",  "2026-05-01", None,
         "SFMO — required before rough electrical", None),
        ("Plumbing Permit",           "pending",  "2026-05-01", None,
         "Required before rough plumbing", None),
        ("Mechanical / HVAC Permit",  "pending",  "2026-05-01", None,
         "Required before rough HVAC", None),
        ("Rough-In Inspection",       "pending",  "2026-08-01", None,
         "After framing + all rough trades complete", None),
        ("Final Inspection & CO",     "pending",  "2026-12-20", None,
         "All work complete — termite record must be on file", None),
    ]
    c.executemany("""INSERT INTO permits
        (name, status, required_date, issued_date, notes, document_path)
        VALUES (?,?,?,?,?,?)""", permits_data)

    conn.commit()
    print("✅ Crowe's Nest Build seeded — Foundation complete, Framing up next.")
