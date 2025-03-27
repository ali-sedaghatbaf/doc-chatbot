import os

from src.models import Document
from src.parser import parser
from src.utils import pdf_to_image


def read_doc(doc_path: str) -> Document:
    doc_name = os.path.splitext(os.path.basename(doc_path))[0]
    doc_images = pdf_to_image(doc_path)
    doc = parser().parse_document(doc_name, doc_path, doc_images)
    return doc
