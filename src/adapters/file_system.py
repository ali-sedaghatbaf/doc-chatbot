import os

from src.models import Document
from src.parser import pdf_parser


def read_doc(doc_path: str) -> Document:
    doc_name = os.path.splitext(os.path.basename(doc_path))[0]
    doc = pdf_parser().parse_document(doc_name, doc_path)
    with open(f"data/{doc_name}.json", "w") as f:
        f.write(doc.model_dump_json())
    return doc
