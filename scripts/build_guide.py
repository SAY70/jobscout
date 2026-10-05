"""Build docs/jobscout-guide.pdf from the markdown guide and screenshots.

    pip install reportlab
    python scripts/build_guide.py

Handles the markdown the guide uses: headings, paragraphs, bullet and
numbered lists, tables, code blocks, quotes, bold, italic, inline code and
links. Screenshots are placed after the heading named in SHOTS.
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
IMG = DOCS / "img"
OUT = DOCS / "jobscout-guide.pdf"

CHAPTERS = [
    "01-start.md",
    "02-profile.md",
    "03-search.md",
    "04-tracker.md",
    "05-publish.md",
    "06-command-line.md",
    "profile-prompt.md",
    "faq.md",
]

# screenshot file -> (chapter, heading it follows, caption)
SHOTS = [
    ("01-start.png", "01-start.md", "Option 1 · In your browser (easiest)",
     "Step 1 in the app: what jobscout does, and where to upload last time's files."),
    ("02a-profile-form.png", "02-profile.md", "Way A · Fill in a form (no AI at all)",
     "Step 2: upload a CV, then pick a way to make the profile."),
    ("02b-profile-chatbot.png", "02-profile.md", "Way B · Use any free chatbot",
     "Way B: the app builds the full prompt, with your CV in it, ready to copy."),
    ("02c-profile-check.png", "02-profile.md", "Check and save your profile",
     "After 'Create my profile': the profile text, and what the search will use."),
    ("03-search.png", "03-search.md", "What happens in one search",
     "Step 3: one search found 31 positions across six boards in about 15 seconds."),
    ("04-tracker.png", "04-tracker.md", "The numbers at the top",
     "Step 4: counts, filters, sorting, and the table. Status and notes are editable."),
    ("04b-tracker-save.png", "04-tracker.md", "Keep your work",
     "Download your positions, a spreadsheet, or a standalone tracker page."),
]

# The PDF fonts lack emoji. The guide always puts a word after each one
# ("✅ yes"), so dropping the symbol loses nothing.
EMOJI = {"\ufe0f": "", "✅ ": "", "❌ ": "", "⚠ ": "", "❔ ": "", "⋮": "..."}

INK = colors.HexColor("#16202A")
MUTED = colors.HexColor("#5C6975")
ACCENT = colors.HexColor("#1F5F8B")
LINE = colors.HexColor("#DCE2E8")
SOFT = colors.HexColor("#EFF2F5")


def fonts() -> tuple[str, str, str, str, str]:
    """Arial and Consolas from Windows if present, else the PDF built-ins."""
    win = Path("C:/Windows/Fonts")
    wanted = {
        "Body": "arial.ttf", "Body-Bold": "arialbd.ttf",
        "Body-Italic": "ariali.ttf", "Body-BoldItalic": "arialbi.ttf",
        "Mono": "consola.ttf",
    }
    if all((win / f).is_file() for f in wanted.values()):
        for name, f in wanted.items():
            pdfmetrics.registerFont(TTFont(name, str(win / f)))
        pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold",
                                      italic="Body-Italic", boldItalic="Body-BoldItalic")
        return "Body", "Body-Bold", "Body-Italic", "Mono", "Body"
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Courier", "Helvetica"


BODY, BOLD, ITALIC, MONO, FAMILY = fonts()

S = {
    "title": ParagraphStyle("title", fontName=BOLD, fontSize=34, leading=40, textColor=INK),
    "subtitle": ParagraphStyle("subtitle", fontName=BODY, fontSize=14, leading=20, textColor=MUTED),
    "h1": ParagraphStyle("h1", fontName=BOLD, fontSize=22, leading=27, textColor=ACCENT,
                         spaceBefore=0, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName=BOLD, fontSize=15, leading=19, textColor=INK,
                         spaceBefore=14, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName=BOLD, fontSize=12, leading=15, textColor=INK,
                         spaceBefore=10, spaceAfter=4),
    "p": ParagraphStyle("p", fontName=FAMILY, fontSize=10.5, leading=15, textColor=INK,
                        spaceAfter=7, alignment=TA_LEFT),
    "cell": ParagraphStyle("cell", fontName=FAMILY, fontSize=9, leading=12, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName=BOLD, fontSize=9, leading=12, textColor=INK),
    "quote": ParagraphStyle("quote", fontName=FAMILY, fontSize=10.5, leading=15,
                            textColor=INK, leftIndent=10, borderPadding=(6, 8, 6, 8),
                            backColor=colors.HexColor("#E3EEF6"), spaceBefore=4, spaceAfter=10),
    "code": ParagraphStyle("code", fontName=MONO, fontSize=8.3, leading=10.8, textColor=INK,
                           backColor=SOFT, borderPadding=7, leftIndent=4, rightIndent=4,
                           spaceBefore=4, spaceAfter=10),
    "caption": ParagraphStyle("caption", fontName=ITALIC, fontSize=9, leading=12,
                              textColor=MUTED, spaceBefore=3, spaceAfter=12),
    "toc1": ParagraphStyle("toc1", fontName=BOLD, fontSize=12, leading=20, textColor=INK),
    "toc2": ParagraphStyle("toc2", fontName=BODY, fontSize=10, leading=15, leftIndent=16,
                           textColor=MUTED),
}


def inline(text: str) -> str:
    """Markdown inline syntax to reportlab's mini-HTML."""
    for k, v in EMOJI.items():
        text = text.replace(k, v)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    codes: list[str] = []

    def keep_code(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", keep_code, text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
                  rf'<link href="\2" color="#1F5F8B"><u>\1</u></link>', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"<b>\1</b>", text)  # links between chapters
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    text = re.sub(r"\x00(\d+)\x00",
                  lambda m: f'<font face="{MONO}" size="9" backColor="#EFF2F5">'
                            f"{codes[int(m.group(1))]}</font>", text)
    return text


class Guide(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in ("h1", "h2"):
            level = 0 if flowable.style.name == "h1" else 1
            text = flowable.getPlainText()
            key = f"h{id(flowable)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
            if level == 0 or not getattr(self, "_toc_h1_only", False):
                self.notify("TOCEntry", (level, text, self.page, key))


def table(rows: list[list[str]], width: float):
    header, *body = rows
    data = [[Paragraph(inline(c), S["cellh"]) for c in header]]
    data += [[Paragraph(inline(c), S["cell"]) for c in r] for r in body]
    n = len(header)
    lengths = [max(len(r[i]) if i < len(r) else 0 for r in rows) for i in range(n)]
    total = sum(min(l, 70) + 8 for l in lengths)
    widths = [width * (min(l, 70) + 8) / total for l in lengths]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def screenshot(name: str, caption: str, width: float):
    path = IMG / name
    if not path.is_file():
        return []
    img = Image(str(path))
    scale = width / img.imageWidth
    img.drawWidth, img.drawHeight = width, img.imageHeight * scale
    img.hAlign = "CENTER"
    frame = Table([[img]], colWidths=[width])
    frame.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, LINE),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return [KeepTogether([frame, Paragraph(caption, S["caption"])])]


def convert(md: str, chapter: str, width: float) -> list:
    shots = {h: (f, c) for f, ch, h, c in SHOTS if ch == chapter}
    out: list = []
    lines = md.splitlines()
    i = 0
    pending_shot = None
    para: list[str] = []

    def flush():
        if para:
            out.append(Paragraph(inline(" ".join(para)), S["p"]))
            para.clear()

    def place_shot():
        nonlocal pending_shot
        if pending_shot:
            out.extend(screenshot(*pending_shot, width))
            pending_shot = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append(Preformatted("\n".join(code), S["code"], maxLineLength=96,
                                    newLineChars=""))
            continue

        m = re.match(r"^(#{1,3})\s+(.*)$", line)
        if m:
            flush()
            place_shot()
            level = len(m.group(1))
            text = m.group(2)
            style = {1: "h1", 2: "h2", 3: "h3"}[level]
            out.append(Paragraph(inline(text), S[style]))
            if text in shots:
                pending_shot = shots[text]
            i += 1
            continue

        if stripped == "---":
            flush()
            i += 1
            continue

        if stripped.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            out.append(table(rows, width))
            out.append(Spacer(1, 8))
            continue

        if stripped.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(Paragraph(inline(" ".join(q for q in quote if q)), S["quote"]))
            continue

        lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if lm:
            flush()
            numbered = lm.group(2)[0].isdigit()
            base = len(lm.group(1))
            items = []
            while i < len(lines):
                lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", lines[i])
                if lm and len(lm.group(1)) <= base:
                    items.append([lm.group(3)])
                elif lm and items:  # nested item: keep it inside its parent
                    items[-1].append(lm.group(3))
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1][-1] += " " + lines[i].strip()  # wrapped line
                else:
                    break
                i += 1
            flow = ListFlowable(
                [ListItem(Paragraph("<br/>• ".join(inline(x) for x in t), S["p"]),
                          leftIndent=16) for t in items],
                bulletType="1" if numbered else "bullet",
                start="1" if numbered else None,
                bulletFontName=BODY, bulletFontSize=9 if not numbered else 10,
                leftIndent=16,
            )
            out.append(flow)
            continue

        if not stripped:
            flush()
            i += 1
            continue

        para.append(stripped)
        i += 1
        # a screenshot goes after the first paragraph under its heading
        if pending_shot and (i >= len(lines) or not lines[i].strip()):
            flush()
            place_shot()

    flush()
    place_shot()
    return out


def page_decor(canvas, doc):
    canvas.saveState()
    canvas.setFont(BODY, 8.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 0.55 * inch, "jobscout guide")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.55 * inch, str(doc.page))
    canvas.setStrokeColor(LINE)
    canvas.line(doc.leftMargin, 0.72 * inch, doc.pagesize[0] - doc.rightMargin, 0.72 * inch)
    canvas.restoreState()


def cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(ACCENT)
    canvas.rect(0, doc.pagesize[1] - 0.45 * inch, doc.pagesize[0], 0.45 * inch, fill=1, stroke=0)
    canvas.restoreState()


def build() -> Path:
    doc = Guide(str(OUT), pagesize=letter, leftMargin=0.9 * inch, rightMargin=0.9 * inch,
                topMargin=0.85 * inch, bottomMargin=0.95 * inch,
                title="jobscout guide", author="jobscout",
                subject="How to find academic jobs with visa sponsorship using jobscout")
    width = doc.width
    story: list = []

    story += [Spacer(1, 1.6 * inch),
              Paragraph("jobscout", S["title"]),
              Spacer(1, 10),
              Paragraph("Find Assistant Professor, Teaching Professor, Research Faculty and "
                        "Research Scientist jobs that fit your CV and sponsor your visa. "
                        "Free, and no AI account needed.", S["subtitle"]),
              Spacer(1, 26),
              Paragraph("<b>The complete guide</b>: getting started, making your profile, "
                        "searching, tracking, publishing the app, and the command line.",
                        S["p"]),
              Spacer(1, 2.2 * inch),
              Paragraph(f"github.com/SAY70/jobscout · {dt.date.today():%B %Y}", S["caption"]),
              PageBreak()]

    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    story += [Paragraph("Contents", S["h3"]), Spacer(1, 6), toc, PageBreak()]

    for name in CHAPTERS:
        md = (DOCS / name).read_text(encoding="utf-8")
        if name == "faq.md":
            md = "# Quick guide and questions\n\n" + md
        story += convert(md, name, width)
        story.append(PageBreak())
    story.pop()

    doc.multiBuild(story, onFirstPage=cover, onLaterPages=page_decor)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size // 1024} KB)")
    sys.exit(0)
