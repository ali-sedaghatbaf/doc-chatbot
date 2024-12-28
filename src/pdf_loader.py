from docling.document_converter import DocumentConverter


def read_doc(doc_name):
    # Load the PDF document
    converter = DocumentConverter()

    text = converter.convert(doc_name).document.export_to_markdown()
    return text
