import sys
sys.path.insert(0, "src")
from pathlib import Path
import pdfplumber

# Pick a recent bulletin
files = sorted(Path("data/raw/bulletins").glob("BCFR_*.pdf"))
print(f"Total bulletins: {len(files)}")
if not files:
    sys.exit()

path = files[-1]
print(f"Examining: {path.name}")

with pdfplumber.open(path) as pdf:
    print(f"Pages: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages[:6]):
        text = page.extract_text(layout=True)
        if text:
            # Show lines with ISIN-like numbers and price tokens
            print(f"\n--- PAGE {i+1} ---")
            for line in text.split("\n")[:40]:
                if "MA" in line and any(ch.isdigit() for ch in line):
                    print(repr(line[:120]))
