"""Ghost-OS Reporting Subsystem.

Exports comprehensive diagnostic reports in standalone HTML, JSON, CSV, and PDF formats.
All exports are self-contained and require zero internet connection.
"""

import csv
import io
import json
import os
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


SKULL_LOGO_B64 = "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"

class ReportExporter:
    """Generates cross-platform diagnostic reports in various formats."""

    @staticmethod
    def export_json(scan_payload: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Serializes scan data to indented JSON."""
        out = json.dumps(scan_payload, indent=2)
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(out)
        return out

    @staticmethod
    def export_csv(scan_payload: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Exports tabular diagnostic tests and hardware summary to CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Header metadata
        writer.writerow(["GHOST-OS HARDWARE DIAGNOSTIC REPORT"])
        writer.writerow(["Scan ID", scan_payload.get("scan_id", "")])
        writer.writerow(["Machine Fingerprint", scan_payload.get("machine_fingerprint", "")])
        writer.writerow(["Platform", scan_payload.get("platform", "")])
        writer.writerow(["OS Version", scan_payload.get("os_version", "")])
        writer.writerow(["Timestamp UTC", scan_payload.get("timestamp_utc", "")])
        writer.writerow([])

        # Diagnostics Table
        writer.writerow(["DIAGNOSTIC TEST RESULTS"])
        writer.writerow(["Test Name", "Status", "Metric Value", "Threshold", "Evidence", "Recommendation"])
        for diag in scan_payload.get("diagnostics", []):
            writer.writerow([
                diag.get("test_name", ""),
                diag.get("status", ""),
                diag.get("metric_value", ""),
                diag.get("threshold", ""),
                diag.get("evidence", ""),
                diag.get("recommendation", ""),
            ])
        writer.writerow([])

        # Storage Devices Table
        hw = scan_payload.get("hardware", {})
        writer.writerow(["STORAGE INVENTORY"])
        writer.writerow(["Device ID", "Model", "Interface", "Capacity (GB)", "SMART Status", "Wear %", "Temp (°C)"])
        for st in hw.get("storage", []):
            cap_gb = round(st.get("capacity_bytes", 0) / (1024**3), 1)
            writer.writerow([
                st.get("device_id", ""),
                st.get("model", ""),
                st.get("interface", ""),
                cap_gb,
                st.get("smart_status", ""),
                st.get("wear_level_pct", "N/A"),
                st.get("temp_c", "N/A"),
            ])

        csv_text = output.getvalue()
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                f.write(csv_text)
        return csv_text

    @staticmethod
    def export_html(
        scan_payload: Dict[str, Any],
        health_scores: Optional[Dict[str, Any]] = None,
        diff_report: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """Generates a self-contained, responsive, dark-mode diagnostic report in HTML."""
        hs = health_scores or {"overall_score": 100, "summary": "Hardware healthy"}
        hw = scan_payload.get("hardware", {})
        cpu = hw.get("cpu", {})
        mem = hw.get("memory", {})
        mb = hw.get("motherboard", {})
        bat = hw.get("battery", {})

        diags_html = ""
        for d in scan_payload.get("diagnostics", []):
            st = d.get("status", "PASS")
            badge_color = "#10B981" if st == "PASS" else ("#F59E0B" if st == "WARN" else "#EF4444")
            diags_html += f"""
            <tr style="border-bottom: 1px solid #374151;">
                <td style="padding: 10px 14px; font-weight: 500;">{d.get('test_name', '')}</td>
                <td style="padding: 10px 14px;"><span style="background-color: {badge_color}22; color: {badge_color}; border: 1px solid {badge_color}55; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 700;">{st}</span></td>
                <td style="padding: 10px 14px; color: #9CA3AF;">{d.get('evidence', '')}</td>
                <td style="padding: 10px 14px; color: #D1D5DB;">{d.get('recommendation', 'None')}</td>
            </tr>
            """

        storage_html = ""
        for s in hw.get("storage", []):
            cap_gb = round(s.get("capacity_bytes", 0) / (1024**3), 1)
            storage_html += f"""
            <tr style="border-bottom: 1px solid #374151;">
                <td style="padding: 8px 12px;">{s.get('model', 'Unknown')}</td>
                <td style="padding: 8px 12px;">{s.get('interface', '')}</td>
                <td style="padding: 8px 12px;">{cap_gb} GB</td>
                <td style="padding: 8px 12px;"><span style="color: #10B981; font-weight: 600;">{s.get('smart_status', 'OK')}</span></td>
                <td style="padding: 8px 12px;">{s.get('wear_level_pct', '0')}%</td>
                <td style="padding: 8px 12px;">{s.get('temp_c', 'N/A')}°C</td>
            </tr>
            """

        diff_section = ""
        if diff_report and diff_report.get("changes_detected"):
            changes_rows = ""
            for ch in diff_report.get("changes", []) + diff_report.get("degradations", []):
                changes_rows += f"""
                <li style="margin-bottom: 6px;"><strong>[{ch.get('component')}]</strong> {ch.get('description')}</li>
                """
            diff_section = f"""
            <div style="background: #0A0A0C; border: 1px solid #27272A; border-radius: 8px; padding: 20px; margin-top: 24px; border-left: 4px solid #EF4444;">
                <h3 style="margin-top: 0; color: #EF4444;">Hardware Changes & Degradation Detected</h3>
                <ul style="color: #FFFFFF; padding-left: 20px;">
                    {changes_rows}
                </ul>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Ghost-OS Hardware Intelligence Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #000000;
            color: #FFFFFF;
            margin: 0;
            padding: 30px;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #DC2626;
            padding-bottom: 20px;
        }}
        .card {{
            background: #0A0A0C;
            border: 1px solid #27272A;
            border-radius: 12px;
            padding: 24px;
            margin-top: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.8);
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }}
        .score-box {{
            background: #000000;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
            border: 1px solid #27272A;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            font-size: 14px;
        }}
        th {{
            text-align: left;
            background: #000000;
            padding: 10px 14px;
            color: #EF4444;
            border-bottom: 2px solid #DC2626;
        }}
        td {{
            padding: 12px 14px;
            border-bottom: 1px solid #18181B;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div style="display: flex; align-items: center; gap: 14px;">
                <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAYAAACOEfKtAAAJGElEQVR4nO1ca6wdVRld+57bUlFaWxGLQgRFGoVgIcbgIxLRaG1EDJqoifGHYjTEGBNiUBJ++ItC1KgkGjEmGP3hI0qiRLGWQNRCeChVY7BEGwEpSq2U297W+5plvnPW1/N1Z8499N5p9xzvWclkZvbM3rP32t9+fI9zgDHGGGOMMcZYIhIKgaR924+6ujAc/nxC15Wlp5T82cogkD3SuiSklBYaKG/SyEwpGaH/3wSS7ETS1PiXAXgxgPU6NgDYqDRPX6csBwHsAfB7APemlP4Qy5ZEFiPyhEodyQlvKMl3k/wOyUdJHuHSsYvkF0huCt+y8otNS42DIk7X7yP5cA0RFckFkvMk57JjPjs8PcI64TaSF2USOdpgX+peIIlzOBkLIm+pWMjInCH5JZJrwxQxmqAkgORGkvergXNqdNOo1CGOR0i+cWRJZJ+8F5H8oxo1y5ODufC9q0eORPbJO43kvVmjThbi1HDdyJDIPnlrSf62EHmOKnz7860nkX3yzib5u8Lk1ZH48RNFYmpitU0pWWVfBWA7gHMAzANoQ4+bqueb68tSSjvzDX1RAtnbqlglXwLgvpaR5zACrZ7/ALAZwDOW2JTWcnSju1SknkL/bZE31zLyvI3WqWcBuEXENaatLLkgHwoktwD4RQslL4fX7x0ppV81NZSXLYEAPh1MTm2GC8tNYepBEQJNYZf0bbTJWZVru/5p9TOJu1hSaAtfp5QEer7XAThVFRsFK4gbaLtaShNYKoFO1gU6j8IQNnRU98tJrtcoSiXnwJdjtGBkVTLUXtgEB0vN7BJ3OkYPvv87V+eiEjiR3XedPRgNrG6ikCa2MXl5SXuuNhBZqS4udbFO5bYxASmcrUKP6TyptIVCRPp3J1SXiZrhasQWJ3A2rG5G3qulb94E4F9h1WtMeR8Cn0L8u7sA3Ahgi+r1eNivWv1QpIPdLETyK8F8dE/2zhkkt8lXQZndl+MDGYZoPvsZybflW5TgXrB6bM4dXyUkcG+4PigX5iojOKX0dErpcwAuBbAjSEUjQyeTOjusU81XvCWldEVK6S4zdFhd5O60tq5RngMAnmiDBL4/9PpvlNbtdZF51LhgPgqSTw5wBDUhdabjdgkSYZ2sPuZm2Kt3H4zPSrosLw4N2E9yXV4xeze8b8P662Eouz/4eOFuUcMeWYT8e8fot4HIS0P+W5VWxnoUenWdiHNcnUteXcPUmO0hX/Uc50j3KTu+SXKDk1EnUZ5O8vqQ7yP+DKUQpOq+ULHvLVYxNSQS+S6SZpvLh2U1wLfh+DXJt4ZyBlpVggQ+GMrf1MQC0tQ8+I0QnvGYzTVKXzVojtGwjsP8TSS/OyRWphLZVw2LhVFH2XGK7t+eOd7Lx9CEnn1n5jz/Mclj1CRVeFJHlzwf6plEnkfyBpL/DPPcbpKfIXlh1gFdEsK1l5/PgWeR/FsY+rcpvbz1nP3K35+R+BDJD5ib8zjLs7K2knwqSIyVffnxNFj1OofkRzUqYt0ajVhYrleuI5vaGyxmT3u8aJ2eVkzfXwA8ovOj0loO6t0zAFwCYKs0hrOlufxJFhOPD3wSwE8B3A7gIQDPyiBwuvJskib0GgDnycnl+77oSLokpbTL3bFogV+4IxK/CODaYJ12laoOz+pICqT0hjo+BOAikWZG209km/5/A9gva7gR+LwB34mWcsv/lJGbUjost0R5gwfDtoXkjzRMfI/mi0uM96vbqsxL5bPzX1XWrSTfq1CRGBtYF+FVZd/IQ+d8/tvR9OrbSEEpJavgBXJex2HhMdGTOlyd84iBqPz78VUtBDYdrE4pTQG4M1h4Jmryp+wbblZzuKTtbLLdhmVNpJR70FY6zUtrQoMGZgumJkelhj8M4FuaEtZpHjN8Vjr1hlB+WqTs/Llfn+bx1GgD2N9Mv5TkoSHaxGJqm2+UP6jyXklyWiuwf+P6RYKWomoXv1d3v7XJMOBliXLq+VZtMt6rFXZQ7y7oW/Z8JrPiRJyv8zYtEK8HcI3SuuanAZLnw3YfgN0hHqYO7ZC+bDN9mSSmLu55Lij910i6TiX5qSA9nsf2f2fKalPp+KHSZkMaw7VJ/vdJXmmuSu0lX0vygbCIua4953vT4ppIRuDWQIY3Lir+1sD1Wd5bMoKroOceCB1gka53ZuXHfD/JyvUhvzkMXTfq/iDWuzjYV8nWSOWqQmUdN4f3J11H1m88IhGRxDpE6YtkdmP+QrmuLl4lqfXy7zDLTa6Ht20Yx8bdQ/KKGpugv297vHzPWGX3PrzjglBlBB41jgbd2M5/Dnm6Yb7+HtoG9smxee3nJN+cP6t595cZEcNg7z2T3RvuzspNoUOvI/kWf95K8hw1DpyuoSGmKd21lhszJf8JkuZXYbjfEaTvBmkl20SeLypfjuXW4UTa/RorOPUcOF1fhCvqAwIYfRux3bNq2/ExGSQcDwC4OdRxj4wOH85cl7dn5fZu+iauzon8EWKjNrH03CI+q0CQKfcbRYT9uui/4b3VwRJjeCGAM/ULzxnV3crYqQ475ttNBpIvhpNu0k6S1JTStFQ3H/qRLJeohez+lKAGWkdc23TM8/GilE8g6WwmrRjlcGBInrXB3jirYV1UuyjnVOnhCPpgNoRzpGA3TCJwYaUTOBWuF7L7nBgjbVW4nsk6YEUSeGBIfZwwaNh2fwssTA+R2BVBILPrqezeVt64KkcC4z96rFgCp7L7xSQq/xXUYbNal/ZtlCbwcHYfV+Uch7SNcUy3wSnUpjlw/ZAhaYvG87M50JBWMoEM15M1sYPMVunovjxZUa+tJJA6m3N90BCO+z5oyxIJ/E94b8VK4JFwnbJF5FAYspWc6amG7LSSJXBqEQncF4LYZ7XgdLJVuThKS6Ahmpo6GZlVGOr7s+dPowUoTeDh8IvypGHr2Bsk9YiOGJVgURDFUWwIs2cltiitu7QCr9LWpNIKu0/bnHlJ4z6R6OEdj3tZWGkEpt4G2FQIWzSuBPA1WahnggN+r4gzcv8uA2nS3LdbjnxD8c10a8DeH5VZMOV75Co1h/onSZ4ffL2vaEV0qZBa4ozqlP4nypElcLG/CM3JDd61Vvx/6hhjjDHGGGOMgYL4H7c3pr6dT5nRAAAAAElFTkSuQmCC" style="width: 44px; height: 44px; object-fit: contain; filter: drop-shadow(0 0 8px #EF4444);" alt="Ghost Skull">
                <div>
                    <h1 style="margin: 0; font-size: 24px; color: #EF4444; letter-spacing: 1px;">GHOST-OS HARDWARE INTELLIGENCE</h1>
                <p style="margin: 4px 0 0 0; color: #A1A1AA; font-size: 13px;">Offline Zero-Footprint Diagnostic Report &bull; Black &bull; Red &bull; White Edition</p>
            </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 12px; color: #EF4444; font-weight: 700;">SCAN TIMESTAMP</div>
                <div style="font-size: 14px; font-weight: 600; color: #FFFFFF;">{scan_payload.get('timestamp_utc')}</div>
            </div>
        </div>

        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h2 style="margin: 0; font-size: 20px; color: #FFFFFF;">Health Evaluation Summary</h2>
                    <p style="margin: 4px 0 0 0; color: #A1A1AA;">{hs.get('summary', '')}</p>
                </div>
                <div style="font-size: 42px; font-weight: 900; color: #FFFFFF;">{hs.get('overall_score', 100)}<span style="font-size: 18px; color: #EF4444;">/100</span></div>
            </div>
            <div class="grid">
                <div class="score-box"><div style="color: #A1A1AA; font-size: 11px; font-weight: 700;">CPU</div><div style="font-size: 20px; font-weight: 900; color: #FFFFFF;">{hs.get('cpu_score', 100)}%</div></div>
                <div class="score-box"><div style="color: #A1A1AA; font-size: 11px; font-weight: 700;">RAM</div><div style="font-size: 20px; font-weight: 900; color: #FFFFFF;">{hs.get('ram_score', 100)}%</div></div>
                <div class="score-box"><div style="color: #A1A1AA; font-size: 11px; font-weight: 700;">STORAGE</div><div style="font-size: 20px; font-weight: 900; color: #FFFFFF;">{hs.get('storage_score', 100)}%</div></div>
                <div class="score-box"><div style="color: #A1A1AA; font-size: 11px; font-weight: 700;">BATTERY</div><div style="font-size: 20px; font-weight: 900; color: #FFFFFF;">{hs.get('battery_score', 100)}%</div></div>
                <div class="score-box"><div style="color: #A1A1AA; font-size: 11px; font-weight: 700;">THERMALS</div><div style="font-size: 20px; font-weight: 900; color: #FFFFFF;">{hs.get('thermal_score', 100)}%</div></div>
            </div>
        </div>

        {diff_section}

        <div class="card">
            <h3 style="margin-top: 0; color: #EF4444;">Machine Identity & Specifications</h3>
            <div class="grid">
                <div><strong style="color: #A1A1AA;">Fingerprint:</strong><br><span style="font-family: monospace; font-size: 11px; color: #EF4444;">{scan_payload.get('machine_fingerprint')}</span></div>
                <div><strong style="color: #A1A1AA;">Platform / OS:</strong><br>{scan_payload.get('platform')} ({scan_payload.get('os_version')})</div>
                <div><strong style="color: #A1A1AA;">Motherboard:</strong><br>{mb.get('manufacturer')} {mb.get('product')} (BIOS {mb.get('bios_version')})</div>
                <div><strong style="color: #A1A1AA;">Processor:</strong><br>{cpu.get('model')} ({cpu.get('physical_cores')}C / {cpu.get('logical_threads')}T)</div>
                <div><strong style="color: #A1A1AA;">Memory:</strong><br>{round(mem.get('total_bytes', 0)/(1024**3), 1)} GB ({mem.get('slots_used')}/{mem.get('slots_total')} slots)</div>
                <div><strong style="color: #A1A1AA;">Battery Health:</strong><br>{bat.get('health_pct', 'N/A')}% ({bat.get('cycle_count', 'N/A')} cycles)</div>
            </div>
        </div>

        <div class="card">
            <h3 style="margin-top: 0;">Diagnostic Health Tests</h3>
            <table>
                <thead>
                    <tr>
                        <th>Test Item</th>
                        <th>Status</th>
                        <th>Evidence</th>
                        <th>Recommendation</th>
                    </tr>
                </thead>
                <tbody>
                    {diags_html}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h3 style="margin-top: 0;">Storage Disks & SMART Status</h3>
            <table>
                <thead>
                    <tr>
                        <th>Drive Model</th>
                        <th>Interface</th>
                        <th>Capacity</th>
                        <th>SMART Status</th>
                        <th>Wear Level</th>
                        <th>Temperature</th>
                    </tr>
                </thead>
                <tbody>
                    {storage_html}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        return html_content

    @staticmethod
    def export_pdf(
        scan_payload: Dict[str, Any],
        health_scores: Optional[Dict[str, Any]] = None,
        diff_report: Optional[Dict[str, Any]] = None,
        output_path: str = "report.pdf",
    ) -> str:
        """Generates an executive PDF diagnostic report using ReportLab."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "GhostTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=6,
        )
        subtitle_style = ParagraphStyle(
            "GhostSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#475569"),
            spaceAfter=14,
        )
        section_heading = ParagraphStyle(
            "GhostSection",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#1E293B"),
            spaceBefore=12,
            spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "GhostBody",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#1E293B"),
        )

        elements = []

        # Title & Subtitle
        elements.append(Paragraph("GHOST-OS HARDWARE INTELLIGENCE REPORT", title_style))
        elements.append(Paragraph(f"Offline Diagnostic & Vault Verification &bull; Generated: {scan_payload.get('timestamp_utc')}", subtitle_style))
        elements.append(Spacer(1, 10))

        # Identity Table
        hw = scan_payload.get("hardware", {})
        mb = hw.get("motherboard", {})
        cpu = hw.get("cpu", {})
        mem = hw.get("memory", {})
        hs = health_scores or {"overall_score": 100, "summary": "Healthy"}

        id_data = [
            [
                Paragraph("<b>Machine Fingerprint:</b>", body_style),
                Paragraph(f"<font size=7>{scan_payload.get('machine_fingerprint')}</font>", body_style),
            ],
            [
                Paragraph("<b>Platform & OS:</b>", body_style),
                Paragraph(f"{scan_payload.get('platform')} &bull; {scan_payload.get('os_version')}", body_style),
            ],
            [
                Paragraph("<b>Motherboard:</b>", body_style),
                Paragraph(f"{mb.get('manufacturer')} {mb.get('product')} (BIOS {mb.get('bios_version')})", body_style),
            ],
            [
                Paragraph("<b>Processor (CPU):</b>", body_style),
                Paragraph(f"{cpu.get('model')} ({cpu.get('physical_cores')} Cores / {cpu.get('logical_threads')} Threads)", body_style),
            ],
            [
                Paragraph("<b>Total Memory:</b>", body_style),
                Paragraph(f"{round(mem.get('total_bytes', 0)/(1024**3), 1)} GB ({mem.get('slots_used')}/{mem.get('slots_total')} Slots Used)", body_style),
            ],
            [
                Paragraph("<b>Overall Health Score:</b>", body_style),
                Paragraph(f"<b><font size=12 color='#059669'>{hs.get('overall_score', 100)} / 100</font></b> - {hs.get('summary', '')}", body_style),
            ],
        ]

        t_id = Table(id_data, colWidths=[140, 400])
        t_id.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_id)
        elements.append(Spacer(1, 14))

        # Diagnostics Table
        elements.append(Paragraph("Diagnostic Test Results", section_heading))
        diag_rows = [["Test", "Status", "Evidence", "Recommendation"]]
        for d in scan_payload.get("diagnostics", []):
            diag_rows.append([
                Paragraph(d.get("test_name", ""), body_style),
                Paragraph(f"<b>{d.get('status', '')}</b>", body_style),
                Paragraph(d.get("evidence", ""), body_style),
                Paragraph(d.get("recommendation", ""), body_style),
            ])

        t_diag = Table(diag_rows, colWidths=[120, 50, 210, 160])
        t_diag.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(t_diag)
        elements.append(Spacer(1, 14))

        # Storage Devices Table
        elements.append(Paragraph("Storage Devices & SMART Health", section_heading))
        storage_rows = [["Device ID", "Model", "Interface", "Capacity", "SMART", "Wear %"]]
        for st in hw.get("storage", []):
            cap_gb = round(st.get("capacity_bytes", 0) / (1024**3), 1)
            storage_rows.append([
                Paragraph(st.get("device_id", ""), body_style),
                Paragraph(st.get("model", ""), body_style),
                Paragraph(st.get("interface", ""), body_style),
                Paragraph(f"{cap_gb} GB", body_style),
                Paragraph(st.get("smart_status", ""), body_style),
                Paragraph(f"{st.get('wear_level_pct', 'N/A')}%", body_style),
            ])

        t_st = Table(storage_rows, colWidths=[90, 160, 60, 80, 80, 70])
        t_st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(t_st)

        doc.build(elements)
        return output_path
