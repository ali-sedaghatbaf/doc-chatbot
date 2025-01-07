import wikipedia
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper


def read_doc(doc_name):
    wikipedia_qr = WikipediaQueryRun(
        api_wrapper=WikipediaAPIWrapper(doc_content_chars_max=10000)
    )
    page = wikipedia.page(doc_name)
    return wikipedia_qr.run(doc_name), page.fullurl if page.exists() else None
