"""Generate a printable FIELD MEASUREMENT SHEET PDF.

A paper fallback for the app's Measurements page -- take this to the framed
house to record tape readings if the app/service is unavailable. Pulls the same
model dimensions as the app (utils/measurement_seed.py) so it always matches.

Standalone -- does not touch the app DB.
Run:    python scripts/generate_measurement_sheet_pdf.py
Output: exports/measurement_sheet.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import date
from fpdf import FPDF

# Make the project importable when run from anywhere
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from utils.measurement_seed import _DATA, _ft_in   # same source as the app

OUTPUT = ROOT / "exports" / "measurement_sheet.pdf"

PROJECT_NAME = "Crowe's Nest Build"
ADDRESS = "450 SR 27, Whitwell, TN 37397"

# Pretty section order + headers
SECTION_TITLES = {
    "Envelope": "Overall Envelope",
    "Division lines": "Interior Division Lines (x from west wall)",
    "Rooms": "Rooms",
    "Openings": "Doors & Windows",
}
SECTION_ORDER = ["Envelope", "Division lines", "Rooms", "Openings"]


class Sheet(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, "FIELD MEASUREMENT SHEET", ln=1)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, f"{PROJECT_NAME}  -  {ADDRESS}", ln=1)
        self.cell(0, 5, f"Printed {date.today():%b %d, %Y}     "
                        f"Measured by: ______________   Date: ____________", ln=1)
        self.ln(1)
        self.set_draw_color(120, 120, 120)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, "Model values from FreeCAD house model. "
                        "Write tape readings in ACTUAL; circle/star anything that differs.",
                  align="C")
        self.set_text_color(0, 0, 0)


def section_heading(pdf, text):
    if pdf.get_y() > pdf.h - 40:
        pdf.add_page()
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 7, text, ln=1, fill=True)
    pdf.ln(1)


def table_header(pdf, item_w, cols):
    """cols = list of (label, width). One model+actual pair per dimension col."""
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(item_w, 6, "Item", border=1, fill=True)
    for label, w in cols:
        pdf.cell(w, 6, label, border=1, align="C", fill=True)
    pdf.ln()


def build():
    pdf = Sheet(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Group the seed data by category
    by_cat = {}
    for cat, item, dims in _DATA:
        by_cat.setdefault(cat, []).append((item, dims))

    EPS = 38   # item column width

    for cat in SECTION_ORDER:
        if cat not in by_cat:
            continue
        section_heading(pdf, SECTION_TITLES.get(cat, cat))

        if cat in ("Envelope", "Division lines"):
            # Simple 2-col: model | ACTUAL blank
            table_header(pdf, 70, [("Model", 40), ("ACTUAL", 70)])
            pdf.set_font("Helvetica", "", 8)
            for item, dims in by_cat[cat]:
                for d in dims:
                    dim, val = d[0], d[1]
                    label = d[2] if len(d) > 2 else _ft_in(val)
                    name = f"{item}  ({dim})" if dim not in ("x",) else item
                    pdf.cell(70, 7, name, border=1)
                    pdf.cell(40, 7, label, border=1, align="C")
                    pdf.cell(70, 7, "", border=1)
                    pdf.ln()
            pdf.ln(3)

        elif cat == "Rooms":
            # Width x Depth, each with a blank actual
            table_header(pdf, 46, [("W (model)", 26), ("W ACTUAL", 32),
                                   ("D (model)", 26), ("D ACTUAL", 32)])
            pdf.set_font("Helvetica", "", 8)
            for item, dims in by_cat[cat]:
                dd = {x[0]: x[1] for x in dims}
                w_lbl = _ft_in(dd.get("width", 0))
                d_lbl = _ft_in(dd.get("depth", 0))
                pdf.cell(46, 7, item, border=1)
                pdf.cell(26, 7, w_lbl, border=1, align="C")
                pdf.cell(32, 7, "", border=1)
                pdf.cell(26, 7, d_lbl, border=1, align="C")
                pdf.cell(32, 7, "", border=1)
                pdf.ln()
            pdf.ln(3)

        elif cat == "Openings":
            # Width x Height (+sill), each width/height with a blank actual
            table_header(pdf, 70, [("W (model)", 20), ("W ACT", 24),
                                   ("H (model)", 20), ("H ACT", 24)])
            pdf.set_font("Helvetica", "", 7.5)
            for item, dims in by_cat[cat]:
                dd = {x[0]: x[1] for x in dims}
                w_lbl = _ft_in(dd.get("width", 0))
                h_lbl = _ft_in(dd.get("height", 0))
                if pdf.get_y() > pdf.h - 22:
                    pdf.add_page()
                    table_header(pdf, 70, [("W (model)", 20), ("W ACT", 24),
                                           ("H (model)", 20), ("H ACT", 24)])
                    pdf.set_font("Helvetica", "", 7.5)
                pdf.cell(70, 6.5, item, border=1)
                pdf.cell(20, 6.5, w_lbl, border=1, align="C")
                pdf.cell(24, 6.5, "", border=1)
                pdf.cell(20, 6.5, h_lbl, border=1, align="C")
                pdf.cell(24, 6.5, "", border=1)
                pdf.ln()
            pdf.ln(3)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUTPUT))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
