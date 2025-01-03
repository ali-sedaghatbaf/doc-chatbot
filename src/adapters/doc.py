from docling.document_converter import DocumentConverter


def read_doc(doc_name):
    # Load the document
    converter = DocumentConverter()
    doc = converter.convert(doc_name).document
    text = doc.export_to_markdown()
    return text
