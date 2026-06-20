import sys
import pdfplumber

def test_layout(path):
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text(layout=True)
            if text:
                lines = text.split('\n')
                for line in lines[:30]:
                    print(repr(line))

if __name__ == "__main__":
    test_layout(sys.argv[1])
