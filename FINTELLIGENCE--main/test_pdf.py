import sys
import pdfplumber

def test_pdf(path):
    print(f"Testing {path}")
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"Page {i+1} text:")
            text = page.extract_text()
            print(text[:500])
            
            print("Trying with explicit table settings:")
            tables = page.extract_tables({
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
            })
            for j, t in enumerate(tables):
                print(f"Table {j+1} rows: {len(t)}")
                if t:
                    print("Header row:", t[0])

if __name__ == "__main__":
    test_pdf(sys.argv[1])
