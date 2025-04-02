import os
from functools import lru_cache
from typing import List, Literal, Tuple

from marker.config.parser import ConfigParser

# from marker.converters.html import HtmlConverter
# from marker.converters.image import ImageConverter
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from tqdm import tqdm

from src.models import Block, Document, Page, Polygon
from src.utils import html_to_md


class MarkerParser:
    def __init__(self, doc_type: Literal["pdf", "html", "image"] = "pdf"):
        json_config = {
            "output_format": "json",
            "use_llm": True,
            "llm_service": "marker.services.openai.OpenAIService",
            "openai_model": "gemini-1.5-flash",
            "openai_api_key": os.getenv("AI_GATEWAY_API_KEY"),
            "openai_base_url": os.getenv("AI_GATEWAY_BASE_URL"),
            "force_ocr": False,
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

        # elif doc_type == "html":
        #    self.json_converter = HtmlConverter(
        #        config=json_config_parser.generate_config_dict(),
        #        artifact_dict=create_model_dict(),
        #        processor_list=json_config_parser.get_processors(),
        #    )

        # elif doc_type == "image":
        #    self.json_converter = ImageConverter(
        #        config=json_config_parser.generate_config_dict(),
        #        artifact_dict=create_model_dict(),
        #        processor_list=json_config_parser.get_processors(),
        #    )

    def _calculate_relative_position(
        self,
        block_polygon: List[Tuple[float, float]],
        page_polygon: List[Tuple[float, float]],
    ) -> List[Tuple[float, float]]:
        # Calculate the relative position of the block within the page
        block_x1, block_y1 = block_polygon[0]
        block_x2, block_y2 = block_polygon[1]
        block_x3, block_y3 = block_polygon[2]
        block_x4, block_y4 = block_polygon[3]

        page_x1, page_y1 = page_polygon[0]
        page_x2, page_y2 = page_polygon[1]
        page_x3, page_y3 = page_polygon[2]
        page_x4, page_y4 = page_polygon[3]

        page_width = page_x2 - page_x1
        page_height = page_y3 - page_y1

        # Calculate the relative position of the block within the page
        relative_x1 = (block_x1 - page_x1) / page_width
        relative_y1 = (block_y1 - page_y1) / page_height

        relative_x2 = (block_x2 - page_x1) / page_width
        relative_y2 = (block_y2 - page_y1) / page_height

        relative_x3 = (block_x3 - page_x1) / page_width
        relative_y3 = (block_y3 - page_y1) / page_height

        relative_x4 = (block_x4 - page_x1) / page_width
        relative_y4 = (block_y4 - page_y1) / page_height

        return [
            (relative_x1, relative_y1),
            (relative_x2, relative_y2),
            (relative_x3, relative_y3),
            (relative_x4, relative_y4),
        ]

    def parse_document(self, doc_name: str, doc_path: str) -> Document:

        json_doc = self.json_converter(doc_path)

        # Print document structure
        print(f"Document type: {json_doc.block_type}")
        print(f"Number of pages: {len(json_doc.children)}")

        pages = []

        # Iterate through pages and blocks
        for page_num, page in tqdm(enumerate(json_doc.children, 1)):
            blocks = []

            for block in page.children:
                relative_position = self._calculate_relative_position(
                    block.polygon, page.polygon
                )
                blocks.append(
                    Block(
                        id=block.id,
                        type=block.block_type,
                        text=html_to_md(block.html),
                        position=Polygon(
                            p1=relative_position[0],
                            p2=relative_position[1],
                            p3=relative_position[2],
                            p4=relative_position[3],
                        ),
                    )
                )

            pages.append(
                Page(
                    id=page.id,
                    number=page_num,
                    blocks=blocks,
                )
            )

        document = Document(
            name=doc_name,
            address=doc_path,
            pages=pages,
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
