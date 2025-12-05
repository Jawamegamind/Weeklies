# scripts/build_docs.py
import pathlib, html, sys
from markdown import markdown

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "proj2" / "site"
DOCS_SRC = ROOT / "proj2" / "docs"
DOCS_OUT = SITE / "docs"

def wrap_html(title, body, rel_css):
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{rel_css}">
</head><body class="pdoc"><main class="pdoc">
<article>{body}</article>
<p><a href="../proj2.html">← Back to API Reference</a></p>
</main></body></html>"""

def build_markdown_pages():
    try:
        DOCS_OUT.mkdir(parents=True, exist_ok=True)
        md_files = list(DOCS_SRC.glob("*.md"))
        if not md_files:
            print(f"⚠️  No markdown files found in {DOCS_SRC}")
            return
        
        for md in md_files:
            try:
                title = md.stem.replace("-", " ").title()
                body = markdown(md.read_text(encoding="utf-8"), extensions=["tables","fenced_code"])
                (DOCS_OUT / f"{md.stem}.html").write_text(
                    wrap_html(title, body, "../assets/custom.css"), encoding="utf-8"
                )
                print(f"✓ Generated: {md.stem}.html")
            except Exception as e:
                print(f"❌ Error processing {md.name}: {e}", file=sys.stderr)
                raise
    except Exception as e:
        print(f"❌ Error building markdown pages: {e}", file=sys.stderr)
        raise

def write_index_html():
    try:
        (SITE / "index.html").write_text(
            """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Project Docs</title>
<link rel="stylesheet" href="assets/custom.css">
</head><body class="pdoc"><main class="pdoc">
<h1>Project Documentation</h1>
<ul>
  <li><a href="proj2.html">🧩 API Reference (pdoc)</a></li>
</ul>
</main></body></html>""",
            encoding="utf-8"
        )
        print("✓ Generated: index.html")
    except Exception as e:
        print(f"❌ Error writing index.html: {e}", file=sys.stderr)
        raise

if __name__ == "__main__":
    print(f"📚 Building documentation...")
    print(f"   ROOT: {ROOT}")
    print(f"   SITE: {SITE}")
    print(f"   DOCS_SRC: {DOCS_SRC}")
    print(f"   DOCS_OUT: {DOCS_OUT}")
    
    # Verify site directory exists
    if not SITE.exists():
        print(f"❌ Error: {SITE} does not exist. Did pdoc build complete?", file=sys.stderr)
        sys.exit(1)
    
    build_markdown_pages()
    write_index_html()
    print("✅ Documentation build complete!")
