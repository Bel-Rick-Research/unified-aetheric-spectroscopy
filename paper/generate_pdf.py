#!/usr/bin/env python3
"""
Builds a publication-quality PDF of Unified Aetheric Standing-Wave Spectroscopy (Paper 4).
Converts Markdown -> HTML (with KaTeX rendering) -> PDF via Brave Headless.
"""

import os
import re
import shutil
import subprocess
import sys
import markdown

PAPER_DIR = os.path.dirname(os.path.abspath(__file__))
MD_PATH = os.path.join(PAPER_DIR, "UNIFIED-AETHERIC-SPECTROSCOPY.md")
HTML_STAGE1 = "/tmp/unified_aetheric_stage1.html"
HTML_STAGE2 = "/tmp/unified_aetheric_stage2.html"
PDF_OUT = os.path.join(PAPER_DIR, "UNIFIED-AETHERIC-SPECTROSCOPY.pdf")


def build_pdf():
    print(f"Reading markdown from: {MD_PATH}")
    with open(MD_PATH, "r", encoding="utf-8") as f:
        md_text = f.read()

    # Strip top navigation links from the print document
    md_text = re.sub(r'^\[←.*?\]\(.*?\)\s*(\|.*?)?\n+', '', md_text, flags=re.MULTILINE)

    # Protect formulas from markdown mangling
    math_blocks = []
    math_inlines = []

    def save_block_math(match):
        math_blocks.append(match.group(0))
        return f"%%MATHBLOCK{len(math_blocks)-1}%%"

    def save_inline_math(match):
        math_inlines.append(match.group(0))
        return f"%%MATHINLINE{len(math_inlines)-1}%%"

    processed_md = re.sub(r'\$\$(.*?)\$\$', save_block_math, md_text, flags=re.DOTALL)
    processed_md = re.sub(r'(?<!\$)\$([^\$\n]+?)\$(?!\$)', save_inline_math, processed_md)

    body_html = markdown.markdown(
        processed_md,
        extensions=['extra', 'tables', 'codehilite', 'toc']
    )

    for i, m in enumerate(math_blocks):
        body_html = body_html.replace(f"%%MATHBLOCK{i}%%", m)
    for i, m in enumerate(math_inlines):
        body_html = body_html.replace(f"%%MATHINLINE{i}%%", m)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Unified Aetheric Standing-Wave Spectroscopy</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body, {{
            delimiters: [
              {{left: '$$', right: '$$', display: true}},
              {{left: '$', right: '$', display: false}}
            ],
            throwOnError: false
        }});"></script>
<style>
    @page {{
        size: A4 portrait;
        margin: 20mm 15mm 20mm 15mm;
        @bottom-right {{
            content: counter(page);
        }}
    }}
    body {{
        font-family: 'Liberation Serif', 'Times New Roman', serif;
        font-size: 10.5pt;
        line-height: 1.45;
        color: #111;
        margin: 0;
        padding: 0;
    }}
    h1 {{
        font-size: 17pt;
        text-align: center;
        margin-bottom: 18px;
        line-height: 1.25;
        color: #000;
    }}
    h2 {{
        font-size: 12.5pt;
        border-bottom: 1px solid #ccc;
        padding-bottom: 3px;
        margin-top: 20px;
        margin-bottom: 8px;
        color: #1a1a1a;
        page-break-after: avoid;
    }}
    h3 {{
        font-size: 11pt;
        margin-top: 14px;
        margin-bottom: 5px;
        color: #222;
        page-break-after: avoid;
    }}
    p {{
        margin-top: 4px;
        margin-bottom: 8px;
        text-align: justify;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0;
        font-size: 9pt;
        page-break-inside: avoid;
    }}
    th, td {{
        border: 1px solid #bbb;
        padding: 4.5pt 6pt;
        text-align: left;
    }}
    th {{
        background-color: #f2f2f2;
        font-weight: bold;
    }}
    code {{
        font-family: 'Liberation Mono', monospace;
        font-size: 8.5pt;
        background-color: #f8f8f8;
        padding: 1px 3px;
        border-radius: 2px;
    }}
    blockquote {{
        border-left: 3px solid #2b4c7e;
        background: #f8fafd;
        margin: 10px 0;
        padding: 6px 12px;
        font-style: italic;
    }}
</style>
</head>
<body>
{body_html}
</body>
</html>
"""

    print(f"Writing Stage 1 HTML: {HTML_STAGE1}")
    with open(HTML_STAGE1, "w", encoding="utf-8") as f:
        f.write(full_html)

    print("Executing KaTeX DOM expansion via Brave Headless...")
    dump_cmd = f"flatpak run --command=sh com.brave.Browser -c 'brave --headless --no-sandbox --dump-dom {HTML_STAGE1}' > {HTML_STAGE2}"
    subprocess.run(dump_cmd, shell=True, check=True)

    tmp_pdf = "/tmp/unified_aetheric_spectroscopy.pdf"
    print(f"Generating PDF via Brave Headless: {tmp_pdf}")
    pdf_cmd = f"flatpak run com.brave.Browser --headless --no-sandbox --print-to-pdf={tmp_pdf} {HTML_STAGE2}"
    subprocess.run(pdf_cmd, shell=True, check=True)

    shutil.copyfile(tmp_pdf, PDF_OUT)

    if os.path.exists(PDF_OUT):
        sz = os.path.getsize(PDF_OUT)
        print(f"SUCCESS: PDF generated ({sz:,} bytes) at {PDF_OUT}")
        return True
    else:
        print("ERROR: PDF file not found!")
        return False


if __name__ == "__main__":
    if not build_pdf():
        sys.exit(1)
