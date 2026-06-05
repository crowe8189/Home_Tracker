"""
Built-in snapshot of the FreeCAD house-model measurement schedule.

This seeds the `measurements` table so the app works even when the FreeCAD CSV
export (house_measurements.csv) isn't present on the deploy. When you re-run the
FreeCAD macro and import the fresh CSV, model values refresh and any actuals you
entered are preserved (matched by `key`).

Keep `_slug` IDENTICAL to the FreeCAD macro's _slug so keys line up on import.
All values are in FEET.
"""


def _slug(s):
    out = []
    for ch in s.lower():
        out.append(ch if ch.isalnum() else "_")
    return "_".join("".join(out).split("_")).strip("_")


def _ft_in(v):
    sign = "-" if v < 0 else ""
    v = abs(v)
    ft = int(v)
    inch = round((v - ft) * 12.0)
    if inch == 12:
        ft += 1
        inch = 0
    return "%s%d'-%d\"" % (sign, ft, inch)


def _row(cat, item, dim, val_ft, label=None):
    return {
        "key": "%s__%s__%s" % (_slug(cat), _slug(item), _slug(dim)),
        "category": cat,
        "item": item,
        "dimension": dim,
        "model_value_ft": float(val_ft),
        "model_value_label": label if label else _ft_in(val_ft),
    }


# (category, item, [(dimension, value_ft, optional_label), ...])
_DATA = [
    # ---- Envelope ----
    ("Envelope", "Main rectangle", [("width", 67.0), ("depth", 32.0)]),
    ("Envelope", "Right wing", [("back_y", 32.0)]),
    ("Envelope", "Walls", [("height", 9.0), ("thickness_in", 6.0, "6 in")]),
    # ---- Division lines (x from west wall) ----
    ("Division lines", "Bedrooms|Hall", [("x", 13.0)]),
    ("Division lines", "Hall|Open core", [("x", 17.0)]),
    ("Division lines", "Core|Right wing", [("x", 39.0)]),
    ("Division lines", "East column west", [("x", 53.0)]),
    # ---- Rooms (width, depth, corner_x, corner_y) ----
    ("Rooms", "BR #1", [("width", 17.0), ("depth", 12.0), ("corner_x", 0.0), ("corner_y", 0.0)]),
    ("Rooms", "Bath", [("width", 13.0), ("depth", 7.0), ("corner_x", 0.0), ("corner_y", 12.0)]),
    ("Rooms", "BR #2", [("width", 13.0), ("depth", 13.0), ("corner_x", 0.0), ("corner_y", 19.0)]),
    ("Rooms", "BR1 Closet", [("width", 2.5), ("depth", 9.0), ("corner_x", 14.5), ("corner_y", 0.0)]),
    ("Rooms", "BR3 Closet", [("width", 2.5), ("depth", 9.0), ("corner_x", 14.5), ("corner_y", 35.0)]),
    ("Rooms", "BR2 Closet", [("width", 4.0), ("depth", 2.5), ("corner_x", 0.0), ("corner_y", 16.5)]),
    ("Rooms", "Hall", [("width", 4.0), ("depth", 20.0), ("corner_x", 13.0), ("corner_y", 12.0)]),
    ("Rooms", "M. Bedroom", [("width", 14.0), ("depth", 14.0), ("corner_x", 39.0), ("corner_y", 0.0)]),
    ("Rooms", "M. Bath", [("width", 14.0), ("depth", 9.0), ("corner_x", 53.0), ("corner_y", 0.0)]),
    ("Rooms", "M. Closet", [("width", 14.0), ("depth", 6.0), ("corner_x", 53.0), ("corner_y", 9.0)]),
    ("Rooms", "Laundry", [("width", 14.0), ("depth", 7.0), ("corner_x", 53.0), ("corner_y", 15.0)]),
    ("Rooms", "Office", [("width", 14.0), ("depth", 10.0), ("corner_x", 53.0), ("corner_y", 22.0)]),
    ("Rooms", "R-Hall H", [("width", 10.0), ("depth", 4.0), ("corner_x", 39.0), ("corner_y", 14.0)]),
    ("Rooms", "R-Hall V", [("width", 4.0), ("depth", 18.0), ("corner_x", 49.0), ("corner_y", 14.0)]),
    ("Rooms", "Cloffice", [("width", 10.0), ("depth", 8.0), ("corner_x", 39.0), ("corner_y", 18.0)]),
    ("Rooms", "Pantry", [("width", 10.0), ("depth", 6.0), ("corner_x", 39.0), ("corner_y", 26.0)]),
    ("Rooms", "Open Core", [("width", 22.0), ("depth", 32.0), ("corner_x", 17.0), ("corner_y", 0.0)]),
    ("Rooms", "BR #3", [("width", 17.0), ("depth", 12.0), ("corner_x", 0.0), ("corner_y", 32.0)]),
    ("Rooms", "Front Porch", [("width", 32.0), ("depth", 8.0), ("corner_x", 17.5), ("corner_y", -8.0)]),
    ("Rooms", "Rear Porch", [("width", 22.0), ("depth", 12.0), ("corner_x", 17.0), ("corner_y", 32.0)]),
    ("Rooms", "Carport/Garage", [("width", 28.0), ("depth", 24.0), ("corner_x", 39.0), ("corner_y", 32.0)]),
    # ---- Openings (width, height, optional sill). Named to match FreeCAD export. ----
    ("Openings", "Door 1 (Glass door, S wall y=0'-0\")", [("width", 6.0), ("height", 8.0)]),
    ("Openings", "Door 2 (Glass door, N wall y=32'-0\")", [("width", 3.0), ("height", 8.0)]),
    ("Openings", "Door 3 (Glass door, E wall x=67'-0\")", [("width", 18.0), ("height", 8.0)]),
    ("Openings", "Door 4 (Simple door, N wall y=32'-0\")", [("width", 3.0), ("height", 6.75)]),
    ("Openings", "Door 5 (Simple door, N wall y=32'-0\")", [("width", 3.0), ("height", 3.0)]),
    ("Openings", "Door 6 (Simple door, E wall x=39'-0\")", [("width", 3.5), ("height", 8.0)]),
    ("Openings", "Door 7 (Simple door, W wall x=17'-0\")", [("width", 3.5), ("height", 8.0)]),
    ("Openings", "Door 8 (Simple door, W wall x=13'-0\")", [("width", 2.67), ("height", 6.75)]),
    ("Openings", "Door 9 (Simple door, W wall x=13'-0\")", [("width", 2.67), ("height", 6.75)]),
    ("Openings", "Door 10 (Simple door, N wall y=32'-0\")", [("width", 2.67), ("height", 6.75)]),
    ("Openings", "Door 11 (Simple door, S wall y=12'-0\")", [("width", 2.67), ("height", 6.75)]),
    ("Openings", "Door 12 (Simple door, W wall x=14'-6\")", [("width", 2.5), ("height", 6.75)]),
    ("Openings", "Door 13 (Simple door, W wall x=14'-6\")", [("width", 2.5), ("height", 6.75)]),
    ("Openings", "Door 14 (Simple door, N wall y=19'-0\")", [("width", 2.5), ("height", 6.75)]),
    ("Openings", "Door 15 (Simple door, S wall y=14'-0\")", [("width", 2.67), ("height", 6.75)]),
    ("Openings", "Door 16 (Simple door, E wall x=53'-0\")", [("width", 3.5), ("height", 8.0)]),
    ("Openings", "Door 17 (Simple door, E wall x=53'-0\")", [("width", 2.67), ("height", 6.75)]),
    ("Openings", "Door 18 (Simple door, E wall x=53'-0\")", [("width", 2.67), ("height", 6.75)]),
    ("Openings", "Door 19 (Simple door, S wall y=9'-0\")", [("width", 2.67), ("height", 6.75)]),
    ("Openings", "Door 20 (Simple door, S wall y=15'-0\")", [("width", 2.67), ("height", 6.75)]),
    ("Openings", "Door 21 (Simple door, E wall x=39'-0\")", [("width", 2.67), ("height", 6.75)]),
    ("Openings", "Door 22 (Simple door, N wall y=18'-0\")", [("width", 8.0), ("height", 8.0)]),
    ("Openings", "Window 23 (Fixed, S wall y=0'-0\")", [("width", 5.0), ("height", 4.0), ("sill", 2.5)]),
    ("Openings", "Window 24 (Open 2-pane, S wall y=0'-0\")", [("width", 5.0), ("height", 4.5), ("sill", 2.5)]),
    ("Openings", "Window 25 (Open 2-pane, S wall y=0'-0\")", [("width", 5.0), ("height", 4.5), ("sill", 2.5)]),
    ("Openings", "Window 26 (Fixed, S wall y=0'-0\")", [("width", 5.0), ("height", 4.0), ("sill", 2.5)]),
    ("Openings", "Window 27 (Fixed, N wall y=32'-0\")", [("width", 5.0), ("height", 4.0), ("sill", 2.5)]),
    ("Openings", "Window 28 (Open 1-pane, N wall y=32'-0\")", [("width", 3.0), ("height", 3.0), ("sill", 3.5)]),
    ("Openings", "Window 29 (Open 1-pane, W wall x=0'-0\")", [("width", 3.0), ("height", 5.0), ("sill", 2.0)]),
    ("Openings", "Window 30 (Open 1-pane, W wall x=0'-0\")", [("width", 3.0), ("height", 5.0), ("sill", 2.0)]),
    ("Openings", "Window 31 (Open 1-pane, W wall x=0'-0\")", [("width", 3.0), ("height", 5.0), ("sill", 2.0)]),
    ("Openings", "Window 32 (Open 2-pane, E wall x=67'-0\")", [("width", 4.0), ("height", 4.0), ("sill", 2.5)]),
]


def get_seed_rows():
    rows = []
    for cat, item, dims in _DATA:
        for d in dims:
            dim, val = d[0], d[1]
            label = d[2] if len(d) > 2 else None
            rows.append(_row(cat, item, dim, val, label))
    return rows
