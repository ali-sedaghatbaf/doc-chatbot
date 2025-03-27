from functools import lru_cache
from typing import Literal, List

from marker.config.parser import ConfigParser
from marker.converters.html import HtmlConverter
from marker.converters.image import ImageConverter
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from tqdm import tqdm

from src.models import Block, Document, Page, Polygon


class MarkerParser:
    def __init__(self, doc_type: Literal["pdf", "html", "image"] = "pdf"):
        json_config = {
            "output_format": "json",
        }
        json_config_parser = ConfigParser(json_config)
        
        if doc_type == "pdf":
            self.json_converter = PdfConverter(
                config=json_config_parser.generate_config_dict(),
                artifact_dict=create_model_dict(),
                processor_list=json_config_parser.get_processors(),
                renderer=json_config_parser.get_renderer(),
                llm_service=json_config_parser.get_llm_service(),
            )

        elif doc_type == "html":
            self.json_converter = HtmlConverter(
                config=json_config_parser.generate_config_dict(),
                artifact_dict=create_model_dict(),
                processor_list=json_config_parser.get_processors(),
            )
            
        elif doc_type == "image":
            self.json_converter = ImageConverter(
                config=json_config_parser.generate_config_dict(),
                artifact_dict=create_model_dict(),
                processor_list=json_config_parser.get_processors(),
            )
            

    def parse_document(self, doc_name: str, doc_path: str, doc_images: List[bytes]) -> str:

        json_doc = self.json_converter(doc_path)
        md_doc = self.md_converter(doc_path)
        # Print document structure
        print(f"Document type: {json_doc.block_type}")
        print(f"Number of pages: {len(json_doc.children)}")

        pages = []

        # Iterate through pages and blocks
        for page_num, page in tqdm(enumerate(json_doc.children, 1)):
            blocks = []

            for block in page.children:

                blocks.append(
                    Block(
                        block_id=block.id,
                        block_type=block.block_type,
                        block_text=block.html,
                        block_position=Polygon(
                            p1=block.polygon[0],
                            p2=block.polygon[1],
                            p3=block.polygon[2],
                            p4=block.polygon[3],
                        ),
                    )
                )

            pages.append(
                Page(
                    page_id=page.id,
                    page_number=page_num,
                    page_blocks=blocks,
                    page_position=Polygon(
                        p1=page.polygon[0],
                        p2=page.polygon[1],
                        p3=page.polygon[2],
                        p4=page.polygon[3],
                    ),
                    page_image=doc_images[page_num - 1],
                )
            )

        document = Document(
            document_name=doc_name,
            document_address=doc_path,
            document_pages=pages,
            document_metadata=json_doc.metadata,
        )
        return document


@lru_cache(maxsize=1)
def pdf_parser():
    return MarkerParser(doc_type="pdf")


@lru_cache(maxsize=1)
def html_parser():
    return MarkerParser(doc_type="html")


@lru_cache(maxsize=1)
def image_parser():
    return MarkerParser(doc_type="image")
