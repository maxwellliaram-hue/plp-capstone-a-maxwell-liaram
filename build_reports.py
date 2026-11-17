"""
Builds the stakeholder-facing deliverables in reports/ from the outputs of notebooks 01-03.

Run AFTER the three notebooks:   python src/build_reports.py
Creates: stakeholder_summary.xlsx, dashboard.png, slides.pdf
"""
from pathlib import Path
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from reportlab.lib.pagesizes import landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
REP, TAB, FIG = ROOT / "reports", ROOT / "reports" / "tables", ROOT / "reports" / "figures"
COL = {"Nairobi": "#1F4E79", "Mombasa": "#C0504D", "Nakuru": "#E39B3B", "Eldoret": "#2E8B57", "Kisumu": "#8C8C8C"}

# ------------------------------------------------------------------ data
con = sqlite3.connect(ROOT / "data" / "duka.db")
df = pd.read_sql("SELECT o.*, p.category FROM orders o JOIN products p USING(product_id)", con)
done = df[df.is_completed == 1]
branch = pd.read_csv(TAB / "branch_summary.csv")
kpi = pd.read_csv(TAB / "kpi_scorecard.csv")
monthly = pd.read_csv(TAB / "monthly_branch_category.csv")
K = dict(zip(kpi["KPI"], kpi["Value"]))
con.close()

# =========================================================== 1. EXCEL WORKBOOK
FONT = "Arial"
hdr_fill = PatternFill("solid", fgColor="1F4E79")
thin = Side(style="thin", color="BFBFBF")


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(name=FONT, bold=True, color="FFFFFF")
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


wb = Workbook()

# --- README sheet
ws = wb.active
ws.title = "Read Me"
lines = [
    ("Duka Electronics – H1 2026 stakeholder summary", True),
    ("Source: cleaned sales data (SQLite) from the capstone repository. Simulated data – no real customers.", False),
    ("Revenue = quantity × unit price × (1 − discount %), COMPLETED order lines only (excludes Returned/Cancelled).", False),
    ("Sheets: 'Branch Summary' (one row per branch) · 'Monthly Detail' (month × branch × category) · 'KPI Scorecard'.", False),
    ("How to use: click the filter arrows in the header row of 'Branch Summary' or 'Monthly Detail' to slice the data.", False),
    ("Totals rows use SUBTOTAL so they update when you filter. Growth and share columns are live formulas.", False),
    ("All amounts are in Kenya shillings (KES).", False),
]
for i, (t, b) in enumerate(lines, 1):
    ws.cell(row=i, column=1, value=t).font = Font(name=FONT, bold=b, size=14 if b else 11)
ws.column_dimensions["A"].width = 120

# --- Branch Summary (formulas for growth / total / share / AOV)
ws = wb.create_sheet("Branch Summary")
heads = ["Branch", "Q1 revenue (KES)", "Q2 revenue (KES)", "H1 revenue (KES)", "Q2 vs Q1 growth",
         "Share of H1 revenue", "Order lines", "Avg order value (KES)", "Return rate (%)"]
ws.append(heads)
style_header(ws, 1, len(heads))
b = branch.sort_values("net_revenue", ascending=False).reset_index(drop=True)
n = len(b)
for i, r in b.iterrows():
    x = i + 2
    ws.append([r["branch"], round(r["q1_revenue"]), round(r["q2_revenue"]), f"=B{x}+C{x}", f"=IFERROR(C{x}/B{x}-1,0)",
               f"=D{x}/SUBTOTAL(109,$D$2:$D${n+1})", int(r["order_lines"]), f"=IFERROR(D{x}/G{x},0)",
               round(r["return_rate_pct"], 1)])
tot = n + 3
ws.cell(row=tot, column=1, value="Total (visible rows)")
for col, letter in [(2, "B"), (3, "C"), (4, "D"), (7, "G")]:
    ws.cell(row=tot, column=col, value=f"=SUBTOTAL(109,{letter}2:{letter}{n+1})")
ws.cell(row=tot, column=5, value=f"=IFERROR(C{tot}/B{tot}-1,0)")
ws.cell(row=tot, column=6, value=f"=SUBTOTAL(109,F2:F{n+1})")
ws.cell(row=tot, column=8, value=f"=IFERROR(D{tot}/G{tot},0)")
for c in range(1, 10):
    ws.cell(row=tot, column=c).font = Font(name=FONT, bold=True)
    ws.cell(row=tot, column=c).border = Border(top=Side(style="medium"))
for row in ws.iter_rows(min_row=2, max_row=n + 1):
    for cell in row:
        cell.font = Font(name=FONT)
for r in range(2, tot + 1):
    for c in (2, 3, 4, 8):
        ws.cell(row=r, column=c).number_format = "#,##0"
    ws.cell(row=r, column=5).number_format = "+0.0%;-0.0%;0.0%"
    ws.cell(row=r, column=6).number_format = "0.0%"
    ws.cell(row=r, column=7).number_format = "#,##0"
    ws.cell(row=r, column=9).number_format = "0.0"
ws.auto_filter.ref = f"A1:I{n+1}"
ws.freeze_panes = "B2"
for i, w in enumerate([22, 18, 18, 18, 16, 18, 13, 20, 14], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
ws.row_dimensions[1].height = 32

# --- Monthly Detail
ws = wb.create_sheet("Monthly Detail")
heads = ["Month", "Branch", "Category", "Net revenue (KES)", "Order lines", "Units"]
ws.append(heads)
style_header(ws, 1, len(heads))
m = monthly.sort_values(["month", "branch", "category"]).reset_index(drop=True)
for _, r in m.iterrows():
    ws.append([r["month"], r["branch"], r["category"], round(r["net_revenue"]), int(r["order_lines"]), int(r["units"])])
last = len(m) + 1
for row in ws.iter_rows(min_row=2, max_row=last):
    for cell in row:
        cell.font = Font(name=FONT)
    row[3].number_format = "#,##0"
    row[4].number_format = "#,##0"
    row[5].number_format = "#,##0"
t = last + 2
ws.cell(row=t, column=1, value="Total (visible rows)").font = Font(name=FONT, bold=True)
for col, letter in [(4, "D"), (5, "E"), (6, "F")]:
    c = ws.cell(row=t, column=col, value=f"=SUBTOTAL(109,{letter}2:{letter}{last})")
    c.font = Font(name=FONT, bold=True)
    c.number_format = "#,##0"
ws.auto_filter.ref = f"A1:F{last}"
ws.freeze_panes = "A2"
for i, w in enumerate([12, 14, 16, 20, 13, 10], 1):
    ws.column_dimensions[get_column_letter(i)].width = w

# --- KPI scorecard
ws = wb.create_sheet("KPI Scorecard")
ws.append(["KPI", "Value", "Definition"])
style_header(ws, 1, 3)
for _, r in kpi.iterrows():
    ws.append([r["KPI"], float(r["Value"]), r["Definition"]])
for row in ws.iter_rows(min_row=2, max_row=len(kpi) + 1):
    for cell in row:
        cell.font = Font(name=FONT)
    row[1].number_format = "#,##0.0"
ws.column_dimensions["A"].width = 42
ws.column_dimensions["B"].width = 18
ws.column_dimensions["C"].width = 75
ws.freeze_panes = "A2"
wb.save(REP / "stakeholder_summary.xlsx")
print("saved stakeholder_summary.xlsx")

# ============================================================= 2. DASHBOARD PNG
fig = plt.figure(figsize=(16, 9), facecolor="white")
gs = fig.add_gridspec(4, 4, height_ratios=[0.5, 1.0, 2.6, 2.6], hspace=0.8, wspace=0.28)
ax = fig.add_subplot(gs[0, :]); ax.axis("off")
ax.text(0, 0.65, "Duka Electronics · Sales Performance Dashboard · H1 2026", fontsize=22, fontweight="bold", color="#1F4E79")
ax.text(0, 0.05, "Completed orders only · Filters in the live Looker Studio version: Branch · Month · Category · Channel",
        fontsize=11, color="#555555")
tiles = [("Net revenue", f"{K['Net revenue (KES)']/1e6:,.1f}M KES"), ("Completed order lines", f"{K['Completed order lines']:,.0f}"),
         ("Avg order value", f"{K['Average order value (KES)']:,.0f} KES"), ("Q2 vs Q1 revenue", f"{K['Q2 vs Q1 revenue growth (%)']:+.1f}%")]
for i, (lab, val) in enumerate(tiles):
    a = fig.add_subplot(gs[1, i]); a.axis("off")
    a.add_patch(plt.Rectangle((0, 0), 1, 1, transform=a.transAxes, color="#F2F5F9"))
    a.text(0.5, 0.64, val, ha="center", va="center", fontsize=22, fontweight="bold",
           color="#C0504D" if val.startswith("-") else "#1F4E79")
    a.text(0.5, 0.2, lab, ha="center", va="center", fontsize=12, color="#555555")
a = fig.add_subplot(gs[2, :2])
bm = done.pivot_table(index="month", columns="branch", values="net_revenue", aggfunc="sum") / 1e6
for br in ["Nairobi", "Mombasa", "Nakuru", "Kisumu", "Eldoret"]:
    hl = br in ("Eldoret", "Mombasa", "Nakuru")
    a.plot(bm.index.str[-2:], bm[br], marker="o", lw=3 if hl else 1.6, color=COL[br], alpha=1 if hl else .6)
    a.text(5.1, bm[br].iloc[-1] + {"Mombasa": 0.9, "Nakuru": -0.9, "Kisumu": 0.0}.get(br, 0), br, color=COL[br], va="center", fontsize=10, fontweight="bold")
a.set_xlim(-0.2, 6.2); a.set_xlabel("Month (2026)"); a.set_ylabel("Net revenue (M KES)")
a.set_title("Monthly revenue by branch: Eldoret up, Mombasa & Nakuru down", loc="left", fontweight="bold", fontsize=12)
a.grid(axis="y", alpha=.3); a.spines[["top", "right"]].set_visible(False)
a = fig.add_subplot(gs[2, 2:])
bq = done.pivot_table(index="branch", columns="quarter", values="net_revenue", aggfunc="sum") / 1e6
bq = bq.sort_values("Q2", ascending=False)
x = np.arange(len(bq))
a.bar(x - .2, bq["Q1"], .4, color="#BBBBBB"); a.bar(x + .2, bq["Q2"], .4, color=[COL[i] for i in bq.index])
for i, (br, r) in enumerate(bq.iterrows()):
    g = 100 * (r["Q2"] / r["Q1"] - 1)
    a.text(i + .2, r["Q2"] + 1, f"{g:+.0f}%", ha="center", fontweight="bold", color="#C0504D" if g < 0 else "#2E8B57")
a.set_xticks(x); a.set_xticklabels(bq.index); a.set_ylabel("M KES")
a.set_title("Q1 (grey) vs Q2 (colour) revenue by branch", loc="left", fontweight="bold", fontsize=12)
a.grid(axis="y", alpha=.3); a.set_axisbelow(True); a.spines[["top", "right"]].set_visible(False)
a = fig.add_subplot(gs[3, :2])
cat = done.groupby("category").agg(l=("order_id", "count"), r=("net_revenue", "sum"))
cat = cat.assign(pl=100 * cat.l / cat.l.sum(), pr=100 * cat.r / cat.r.sum()).sort_values("pr")
y = np.arange(len(cat))
a.barh(y + .2, cat.pr, .4, color="#1F4E79", label="% of revenue"); a.barh(y - .2, cat.pl, .4, color="#BBBBBB", label="% of order lines")
a.set_yticks(y); a.set_yticklabels(cat.index); a.legend(frameon=False, loc="center right")
a.set_title("Smartphones + laptops: ~22% of lines, ~73% of revenue", loc="left", fontweight="bold", fontsize=12)
a.spines[["top", "right"]].set_visible(False)
a = fig.add_subplot(gs[3, 2:])
ch = done[done.channel != "Unknown"].pivot_table(index="branch", columns="channel", values="net_revenue", aggfunc="sum")
ch = (ch.div(ch.sum(axis=1), axis=0) * 100).sort_values("Online")
a.barh(ch.index, ch["In-store"], color="#8FA9C4", label="In-store"); a.barh(ch.index, ch["Online"], left=ch["In-store"], color="#1F4E79", label="Online")
a.set_xlabel("% of branch revenue"); a.legend(frameon=False, ncol=2, loc="lower right", bbox_to_anchor=(1, 1))
a.set_title("Sales channel mix is similar in every branch", loc="left", fontweight="bold", fontsize=12)
a.spines[["top", "right"]].set_visible(False)
fig.savefig(REP / "dashboard.png", dpi=130, bbox_inches="tight")
plt.close(fig)
print("saved dashboard.png")

# ================================================================= 3. SLIDES PDF
W, H = 960, 540
pdf = canvas.Canvas(str(REP / "slides.pdf"), pagesize=(W, H))
NAVY, RED, GREEN, GREY = (0.12, 0.31, 0.47), (0.75, 0.31, 0.30), (0.18, 0.55, 0.34), (0.35, 0.35, 0.35)


def slide(title, bullets=None, image=None, img_box=None, notes=None, num=[0]):
    num[0] += 1
    pdf.setFillColorRGB(*NAVY); pdf.rect(0, H - 8, W, 8, fill=1, stroke=0)
    pdf.setFont("Helvetica-Bold", 26); pdf.drawString(40, H - 60, title)
    y = H - 110
    for bl in bullets or []:
        lvl = 1 if bl.startswith("  ") else 0
        txt = bl.strip()
        pdf.setFillColorRGB(*GREY if lvl else (0.1, 0.1, 0.1))
        pdf.setFont("Helvetica", 15 if lvl else 18)
        # simple word wrap
        maxw = (img_box[0] - 60) if image and img_box else W - 100
        words, line = txt.split(), ""
        first = True
        for w_ in words + [None]:
            test = (line + " " + w_).strip() if w_ else line
            if w_ is None or pdf.stringWidth(test, "Helvetica", 15 if lvl else 18) > maxw - 30 * lvl:
                pdf.drawString(50 + 30 * lvl, y, ("• " if first and not lvl else "– " if first else "   ") + line)
                y -= 24 if lvl else 27; line = w_ or ""; first = False
            else:
                line = test
        y -= 8
    if image:
        x, yy, w_, h_ = img_box
        pdf.drawImage(ImageReader(str(image)), x, yy, width=w_, height=h_, preserveAspectRatio=True, anchor="c")
    pdf.setFont("Helvetica", 10); pdf.setFillColorRGB(0.5, 0.5, 0.5)
    pdf.drawString(40, 18, "Duka Electronics · H1 2026 analytics capstone")
    pdf.drawRightString(W - 40, 18, str(num[0]))
    pdf.showPage()


# 1 title
pdf.setFillColorRGB(*NAVY); pdf.rect(0, 0, W, H, fill=1, stroke=0)
pdf.setFillColorRGB(1, 1, 1); pdf.setFont("Helvetica-Bold", 38)
pdf.drawString(60, 330, "Where to focus H2 marketing spend")
pdf.setFont("Helvetica", 22); pdf.drawString(60, 285, "Duka Electronics · Sales performance analysis, H1 2026")
pdf.setFont("Helvetica", 16); pdf.drawString(60, 200, "Junior Data Analyst · PLP End-to-End Capstone"); pdf.drawString(60, 175, "Maxwell Liaram · linkedin.com/in/maxwell-liaram-6227a3382 · maxwellliaram@gmail.com")
pdf.showPage()
slide("The decision and the questions", [
    "Stakeholder: Commercial Director. Decision: where to put H2 2026 marketing spend and management attention.",
    "Q1  Which branches are growing or shrinking?", "Q2  Which products and categories drive revenue?",
    "Q3  Are the changes real or just noise?", "Q4  Are returns or cancellations the cause?",
    "Success = every question answered with a number, one tested hypothesis, three quantified actions."])
slide("Data: 15,816 raw rows, 15,367 trustworthy ones", [
    "Audited on six dimensions: completeness, validity, accuracy, consistency, uniqueness, timeliness.",
    "Fixed: 310 duplicates, 5 spellings of branch names, mixed dates, 46 ×10 price slips, 31 impossible 2027 dates.",
    "Every decision is logged in a reusable cleaning function; personal data removed or pseudonymised."],
    FIG / "01_quality_audit.png", (440, 70, 490, 380))
slide(f"Revenue is flat ({K['Q2 vs Q1 revenue growth (%)']:+.1f}%), but that hides a split", [
    f"Total H1 net revenue: {K['Net revenue (KES)']/1e6:,.0f}M KES.",
    "Eldoret +74%", "Mombasa −27%, Nakuru −29%", "Nairobi +3%, Kisumu +10%"],
    FIG / "03_branch_growth.png", (390, 60, 550, 400))
slide("The split is real, not noise", [
    "Mann-Whitney test on daily revenue, Q1 vs Q2, Bonferroni α = 0.01.",
    "Mombasa −28% (CI −38 to −16), Nakuru −30% (CI −41 to −17): significant.",
    "Eldoret +73% (CI +45 to +106): significant.",
    "Nairobi and Kisumu: indistinguishable from noise."],
    FIG / "03_effect_sizes.png", (400, 90, 540, 340))
slide("Where the money is", [
    "Smartphones + laptops: 22% of order lines, 73% of revenue.",
    "Four SKUs (iPhone-style 15, Galaxy-style S24, UltraSlim 13, ProBook 15) = 58% of revenue.",
    "~85% of the Mombasa/Nakuru decline sits in smartphones and laptops."],
    FIG / "03_category_share.png", (430, 90, 500, 330))
slide("What it is NOT", [
    "Not returns: rates range 4.3–5.7%; Cramér's V = 0.02 (negligible).",
    "Not product mix: category mix is near-identical across branches.",
    "Not discounting: 3.2% of gross, no link to basket size.",
    "So the cause is likely local demand, competition or stock – needs a field check."],
    FIG / "02_branch_category_mix.png", (440, 100, 490, 300))
slide("Recommendations", [
    "1  Launch a Mombasa & Nakuru recovery review now (smartphone/laptop stock, local competitors, staffing). Recovering Q1 run-rate = ~19.8M KES per quarter.",
    "2  Weight H2 marketing toward Eldoret and protect stock: sustaining Q2 run-rate = ~31M KES per quarter.",
    "3  Guarantee availability of the top 4 SKUs (58% of revenue) in every branch.",
    "4  Run an A/B test cutting accessory discounts (0.8M KES spent in H1) before any permanent change.",
    "5  Make payment method and customer ID mandatory at POS (2.8% / 1.7% unknown)."])
slide("Impact, limitations, next steps", [
    "Impact: ~19.8M KES per quarter at stake in two branches; ~13.4M KES per quarter uplift already captured in Eldoret.",
    "Limits: simulated data; one half-year (no seasonality baseline); no cost or margin data; tests cannot explain WHY; 1.7% of sales have unknown customers.",
    "Next: add margin and footfall data, review store-level promotions, repeat the analysis for H2."])
pdf.save()
print("saved slides.pdf")
