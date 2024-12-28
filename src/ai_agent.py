from src import (
    graph_constructor,
    graph_explorer,
    pdf_loader,
    wiki_client,
    wikipedia_client,
)


async def construct_graph(doc_name, doc_type):

    if doc_type == "Wikipedia":
        text = wikipedia_client.read_doc(doc_name)
    elif doc_type == "pdf":
        text = pdf_loader.read_doc(doc_name)
    else:
        text = wiki_client.read_doc(doc_name)

    gc = graph_constructor.GraphCnstructor()
    await gc.process_document(text, doc_name, chunk_size=500, chunk_overlap=100)


def answer_question(question):
    ge = graph_explorer.GraphExplorer()
    response = ge.evaluate({"question": question})
    return response["answer"]
