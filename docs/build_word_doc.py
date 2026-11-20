"""Builds a styled Microsoft Word (.docx) document combining:
1. OFFICIAL_DOCUMENTATION.md
2. SCHEMA_CONTRACT.md
3. USB_PARTITION_SPEC.md
"""

import os
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DOCS_DIR = r"C:\Users\kathu\Desktop\projects\Ghost-OS\docs"
OUTPUT_DOCX = os.path.join(DOCS_DIR, "Ghost-OS_Official_System_Documentation.docx")

FILES_TO_MERGE = [
    ("Part I: System Specification, Architectural Whitepaper & Operator's Handbook",
     os.path.join(DOCS_DIR, "OFFICIAL_DOCUMENTATION.md")),
    ("Part II: Canonical Schema & Database Contract (JSON Schemas & SQLite DDL)",
     os.path.join(DOCS_DIR, "SCHEMA_CONTRACT.md")),
    ("Part III: USB Partition Specification & Storage Layout (GPT & Deployment)",
     os.path.join(DOCS_DIR, "USB_PARTITION_SPEC.md")),
    ("Part IV: Official Operator's Turnkey User Manual (Cross-Platform Field Guide)",
     os.path.join(DOCS_DIR, "USER_MANUAL.md")),
    ("Part V: Physical Hardware Validation & Sensor Benchmark Audit",
     os.path.join(DOCS_DIR, "HARDWARE_VALIDATION_REPORT.md")),
    ("Part VI: Security Hardening Architecture & Independent Evaluator Response",
     os.path.join(DOCS_DIR, "SECURITY_HARDENING_RESPONSE.md")),
]

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def add_heading_with_color(doc, text, level):
    h = doc.add_heading(text, level=level)
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(6)
    h.paragraph_format.keep_with_next = True
    for run in h.runs:
        if level == 1:
            run.font.color.rgb = RGBColor(27, 54, 93)  # Navy
            run.font.size = Pt(20)
            run.font.bold = True
        elif level == 2:
            run.font.color.rgb = RGBColor(15, 76, 129)  # Classic Blue
            run.font.size = Pt(15)
            run.font.bold = True
        elif level == 3:
            run.font.color.rgb = RGBColor(44, 62, 80)   # Slate
            run.font.size = Pt(12.5)
            run.font.bold = True
        elif level == 4:
            run.font.color.rgb = RGBColor(70, 80, 95)
            run.font.size = Pt(11)
            run.font.bold = True
    return h

def format_inline_runs(p, text):
    """Splits markdown inline formatting (**bold**, `code`, etc.) into runs."""
    pattern = r'(\*\*[^*]+\*\*|`[^`]+`)'
    parts = re.split(pattern, text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = p.add_run(part[2:-2])
            run.bold = True
            run.font.name = "Calibri"
        elif part.startswith("`") and part.endswith("`"):
            run = p.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(180, 40, 40)
        else:
            run = p.add_run(part)
            run.font.name = "Calibri"
            run.font.size = Pt(10.5)

def add_code_block(doc, lines):
    """Adds a shaded monospace code box."""
    code_text = "\n".join(lines).strip()
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(6.5)

    cell = table.cell(0, 0)
    set_cell_background(cell, "F4F6F9")
    set_cell_margins(cell, top=120, bottom=120, left=180, right=180)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(code_text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(33, 37, 41)

    # Empty paragraph after table for spacing
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(4)

def add_markdown_table(doc, table_lines):
    """Parses and adds a styled Word table from markdown table rows."""
    if len(table_lines) < 2:
        return

    # Extract rows
    rows_data = []
    for l in table_lines:
        clean = l.strip()
        if not clean or clean.startswith("|-"):
            continue
        # Split by |
        cols = [c.strip() for c in clean.split("|")]
        # remove leading and trailing empty splits if line started/ended with |
        if cols and cols[0] == "":
            cols = cols[1:]
        if cols and cols[-1] == "":
            cols = cols[:-1]
        if cols and not all(set(c).issubset({'-', ':', ' '}) for c in cols):
            rows_data.append(cols)

    if not rows_data:
        return

    num_cols = max(len(r) for r in rows_data)
    num_rows = len(rows_data)

    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    for r_idx, row in enumerate(rows_data):
        for c_idx in range(num_cols):
            cell = table.cell(r_idx, c_idx)
            val = row[c_idx] if c_idx < len(row) else ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)

            if r_idx == 0:
                # Header row
                set_cell_background(cell, "1B365D")  # Dark Navy
                set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
                run = p.add_run(val)
                run.bold = True
                run.font.name = "Calibri"
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(255, 255, 255)
            else:
                # Alternate row shading
                bg_color = "F8FAFC" if (r_idx % 2 == 1) else "FFFFFF"
                set_cell_background(cell, bg_color)
                set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
                format_inline_runs(p, val)

    # Empty paragraph after table
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(6)

def parse_markdown_to_docx(doc, filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    in_code_block = False
    code_lines = []
    in_table = False
    table_lines = []

    for line in lines:
        stripped = line.strip()

        # Handle code blocks
        if stripped.startswith("```"):
            if in_code_block:
                in_code_block = False
                add_code_block(doc, code_lines)
                code_lines = []
            else:
                # Finish any pending table first
                if in_table:
                    add_markdown_table(doc, table_lines)
                    table_lines = []
                    in_table = False
                in_code_block = True
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line.rstrip())
            continue

        # Handle markdown tables
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_lines.append(stripped)
            continue
        else:
            if in_table:
                add_markdown_table(doc, table_lines)
                table_lines = []
                in_table = False

        if not stripped:
            continue

        # Headings
        if stripped.startswith("#### "):
            add_heading_with_color(doc, stripped[5:], level=4)
        elif stripped.startswith("### "):
            add_heading_with_color(doc, stripped[4:], level=3)
        elif stripped.startswith("## "):
            add_heading_with_color(doc, stripped[3:], level=2)
        elif stripped.startswith("# "):
            add_heading_with_color(doc, stripped[2:], level=1)
        elif stripped.startswith("---") or stripped.startswith("***"):
            # Horizontal rule
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(6)
            run = p.add_run("_______________________________________________________________________________")
            run.font.color.rgb = RGBColor(200, 205, 215)
            run.font.size = Pt(8)
        elif re.match(r'^!\[(.*?)\]\((.*?)\)', stripped):
            # Markdown Image
            m = re.match(r'^!\[(.*?)\]\((.*?)\)', stripped)
            alt_text = m.group(1)
            img_rel_path = m.group(2)
            # Resolve image path relative to the markdown file or DOCS_DIR
            img_full_path = os.path.join(os.path.dirname(filepath), img_rel_path)
            if not os.path.exists(img_full_path):
                img_full_path = os.path.join(DOCS_DIR, img_rel_path)
            if os.path.exists(img_full_path):
                img_p = doc.add_paragraph()
                img_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                img_p.paragraph_format.space_before = Pt(8)
                img_p.paragraph_format.space_after = Pt(2)
                r_img = img_p.add_run()
                r_img.add_picture(img_full_path, width=Inches(6.2))

                caption = doc.add_paragraph()
                caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
                caption.paragraph_format.space_before = Pt(2)
                caption.paragraph_format.space_after = Pt(8)
                c_run = caption.add_run(f"Figure: {alt_text}")
                c_run.font.name = "Calibri"
                c_run.font.size = Pt(9.5)
                c_run.font.italic = True
                c_run.font.color.rgb = RGBColor(100, 110, 125)
        elif stripped.startswith("* ") or stripped.startswith("- "):
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            format_inline_runs(p, stripped[2:])
        elif re.match(r'^\d+\.\s', stripped):
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            item_text = re.sub(r'^\d+\.\s', '', stripped)
            format_inline_runs(p, item_text)
        elif stripped.startswith("> "):
            # Blockquote
            table = doc.add_table(rows=1, cols=1)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cell = table.cell(0, 0)
            set_cell_background(cell, "EDF4FC")
            set_cell_margins(cell, top=80, bottom=80, left=160, right=120)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            format_inline_runs(p, stripped[2:])
            sp = doc.add_paragraph()
            sp.paragraph_format.space_before = Pt(0)
            sp.paragraph_format.space_after = Pt(2)
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(5)
            format_inline_runs(p, stripped)

    # Clean up pending structures
    if in_code_block and code_lines:
        add_code_block(doc, code_lines)
    if in_table and table_lines:
        add_markdown_table(doc, table_lines)

def build_complete_document():
    doc = Document()

    # Set page margins to 0.75 in
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # ------------------ COVER PAGE / HEADER ------------------
    cover_title = doc.add_paragraph()
    cover_title.paragraph_format.space_before = Pt(30)
    cover_title.paragraph_format.space_after = Pt(8)
    run_t = cover_title.add_run("GHOST-OS")
    run_t.font.name = "Arial Black"
    run_t.font.size = Pt(36)
    run_t.font.bold = True
    run_t.font.color.rgb = RGBColor(27, 54, 93)  # Dark Navy

    cover_sub = doc.add_paragraph()
    cover_sub.paragraph_format.space_before = Pt(0)
    cover_sub.paragraph_format.space_after = Pt(12)
    run_s = cover_sub.add_run("Universal Portable Hardware Intelligence Platform")
    run_s.font.name = "Calibri"
    run_s.font.size = Pt(18)
    run_s.font.bold = True
    run_s.font.color.rgb = RGBColor(15, 76, 129)  # Classic Blue

    cover_tag = doc.add_paragraph()
    cover_tag.paragraph_format.space_before = Pt(0)
    cover_tag.paragraph_format.space_after = Pt(24)
    run_tag = cover_tag.add_run("Complete Official Specification, Canonical Schema Contracts & Operator's Handbook")
    run_tag.font.name = "Calibri"
    run_tag.font.size = Pt(13)
    run_tag.font.italic = True
    run_tag.font.color.rgb = RGBColor(100, 110, 125)

    # Metadata Table
    meta_data = [
        ("Platform Version", "Ghost-OS Specification & Reference Implementation (v1.0.0-RC1)"),
        ("Architecture", "Dual-Mode (Bootable Linux Live OS + Portable Windows .NET 8 + macOS/ARM64)"),
        ("Storage Security", "Ghost Vault Encrypted (Argon2id KDF: 128 MiB, 3 iters, 4 lanes + XChaCha20-Poly1305)"),
        ("Test Verification", "44 / 44 Automated Tests Passing (100% Green Coverage)"),
        ("Trust Provenance", "Ghost Trust Report (RFC 8032 Asymmetric Ed25519 Public-Key Digital Seal)"),
        ("Transport Security", "TLS 1.3 / Pure-Python x509 Self-Signed Gateway"),
        ("Partition Layout", "Part 1: GhostVault (exFAT) | Part 2: ESP (FAT32) | Part 3: Live OS (ext4)"),
    ]
    meta_table = doc.add_table(rows=len(meta_data), cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx, (label, val) in enumerate(meta_data):
        c0 = meta_table.cell(idx, 0)
        c1 = meta_table.cell(idx, 1)
        set_cell_background(c0, "1B365D")
        set_cell_background(c1, "F8FAFC")
        set_cell_margins(c0, 60, 60, 100, 100)
        set_cell_margins(c1, 60, 60, 100, 100)

        p0 = c0.paragraphs[0]
        r0 = p0.add_run(label)
        r0.bold = True
        r0.font.color.rgb = RGBColor(255, 255, 255)
        r0.font.size = Pt(9.5)

        p1 = c1.paragraphs[0]
        r1 = p1.add_run(val)
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = RGBColor(40, 45, 55)

    doc.add_page_break()

    # ------------------ MERGE 3 DOCUMENTS ------------------
    for idx, (part_title, file_path) in enumerate(FILES_TO_MERGE):
        # Section Header Banner
        banner_table = doc.add_table(rows=1, cols=1)
        banner_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        b_cell = banner_table.cell(0, 0)
        set_cell_background(b_cell, "1B365D")
        set_cell_margins(b_cell, top=140, bottom=140, left=200, right=200)

        bp = b_cell.paragraphs[0]
        bp.paragraph_format.space_before = Pt(4)
        bp.paragraph_format.space_after = Pt(4)
        brun = bp.add_run(part_title.upper())
        brun.font.name = "Arial Black"
        brun.font.size = Pt(13)
        brun.font.bold = True
        brun.font.color.rgb = RGBColor(255, 255, 255)

        sp = doc.add_paragraph()
        sp.paragraph_format.space_before = Pt(6)
        sp.paragraph_format.space_after = Pt(6)

        print(f"Parsing {file_path}...")
        parse_markdown_to_docx(doc, file_path)

        if idx < len(FILES_TO_MERGE) - 1:
            doc.add_page_break()

    # Save document
    print(f"Saving compiled Word document to {OUTPUT_DOCX}...")
    doc.save(OUTPUT_DOCX)
    print("Done! Document created successfully.")

if __name__ == "__main__":
    build_complete_document()
