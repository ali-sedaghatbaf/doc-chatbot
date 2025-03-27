from klarna_wiki_api.sessions import KlarnaWikiSession

from src.utils import wiki_page_to_image


class ParseKlarnaWikiSession(KlarnaWikiSession):
    def get_parsed_content(self, page_title: str) -> str | None:
        if not isinstance(page_title, str):
            raise Exception("page_title must be string!")

        params = {
            "action": "parse",
            "page": page_title,
            "format": "json",
            "prop": "text",
        }
        response = self.get(params=params)

        if page_content := response.get("parse", {}).get("text", {}).get("*"):
            return page_content

        return None


def read_doc(doc_name, chunk_size: int = 1000, chunk_overlap: int = 200):
    base_url = "https://wiki.nonprod.klarna.net/wiki"
    url = f"{base_url}/{doc_name.replace(' ', '_')}"

    png_image = wiki_page_to_image(url)

    return [
        png_image,
    ]
