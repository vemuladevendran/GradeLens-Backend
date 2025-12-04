import re
from PyPDF2 import PdfReader 
class StudentPaperParser:
    def __init__(self, pdf_path: str):
        full_text = ""
        try:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
   
                text = page.extract_text()
                if text:  
                    full_text += text + "\n"
        except FileNotFoundError:
            print(f"Error: The file '{pdf_path}' was not found.")
            raise  
        except Exception as e:
            print(f"An error occurred reading the PDF: {e}")
            raise 
        self.text = full_text.strip()

    def parse(self):
        parts = re.split(r'\n?\s*\d+\.\s*', self.text)

        parts = [p.strip() for p in parts if p.strip()]

        qa_pairs = {}
        for part in parts:
            if '?' in part:
                try:
 
                    q, a = part.split('?', 1)
                    qa_pairs[q.strip() + '?'] = a.strip().replace("\n", "")
                except ValueError:
                    print(f"Warning: Could not parse part: {part}")
        
        return qa_pairs