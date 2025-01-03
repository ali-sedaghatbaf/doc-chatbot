from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper


def read_doc(doc_name):
    wikipedia = WikipediaQueryRun(
        api_wrapper=WikipediaAPIWrapper(doc_content_chars_max=10000)
    )
    return wikipedia.run(doc_name)
