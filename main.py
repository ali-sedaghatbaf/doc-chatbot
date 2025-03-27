import asyncio
import os

import streamlit as st
from dotenv import load_dotenv

from src.adapters import doc, wiki, wikibase, wikipedia
from src.agent import kg_constructor, state_graph

load_dotenv()


async def construct_knowledge_graph(doc_name, doc_type):

    if doc_type == "Wikipedia":
        doc_images, doc_url = wikipedia.read_doc(doc_name)
    elif doc_type == "pdf":
        doc_url = doc_name
        doc_name = os.path.basename(doc_url)
        doc_images = doc.read_doc(doc_url)

    elif doc_type == "Klarna Wiki":
        doc_images, doc_url = wiki.read_doc(doc_name)
    else:
        doc_images, doc_url = wikibase.read_doc(doc_name)
    await kg_constructor.process_document(doc_images, doc_name, doc_url)


def answer_question(question):
    response = state_graph.graph.invoke(
        {"question": question}, {"recursion_limit": 100, "thread_id": 1}
    )
    response_text = response.get("answer", "")
    reponse_citations = response.get("citations", {})

    if reponse_citations:
        response_text += "\n\n\n**References:**"
        for document_name, document_url in response_citations.items():
            response_text += f"\n\n[{document_name}]({document_url})"
    return response_text


def write_message(role, content, save=True):
    """
    This is a helper function that saves a message to the
     session state and then writes a message to the UI
    """
    # Append to session state
    if save:
        st.session_state.messages.append({"role": role, "content": content})

    # Write to UI

    with st.chat_message(role):
        st.markdown(content)


# tag::submit[]
# Submit handler
def handle_submit(message):
    """
    Submit handler:

    You will modify this method to talk with an LLM and provide
    context using data from Neo4j.
    """

    # Handle the response
    with st.spinner("Thinking..."):
        answer = answer_question(message)
        write_message("assistant", answer)


st.set_page_config(page_title="Chatbot", page_icon=":copilot:")

st.title("GR Chatbot")

doc_tab, chat_tab = st.tabs(["Add Documents", "Ask Questions"])
with doc_tab:
    # Section for Adding Documents
    st.subheader("Add a Document to Knowledge Base")
    col1, col2 = st.columns(2)
    with col1:
        doc_name = st.text_input("Document Name:")
    with col2:
        doc_type = st.selectbox(
            "Document Source",
            ("Klarna Wiki", "Klarna Wikibase", "Wikipedia"),
        )
    uploaded_file = st.file_uploader(
        "Upload your text document", type=["pdf", "txt", "docx", "doc", "html"]
    )

    if uploaded_file is not None:
        doc_type = "pdf"
        # Save the uploaded PDF to a temporary location
        doc_name = os.path.join("temp_dir", uploaded_file.name)
        os.makedirs("temp_dir", exist_ok=True)
        with open(doc_name, "wb") as f:
            f.write(uploaded_file.getbuffer())

    if st.button("Add Document"):
        if doc_name:
            with st.spinner("Transferring data..."):
                asyncio.run(construct_knowledge_graph(doc_name, doc_type))
            st.success("Import successful!")
        else:
            st.error("Document name is required!")

with chat_tab:
    # Section for Chat Panel

    st.subheader("Chat Panel for Question Answering")
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Hi, I'm GR Chatbot!  How can I help you?",
            },
        ]
    for message in st.session_state.messages:
        write_message(message["role"], message["content"], save=False)

    # Handle any user input
    if prompt := st.chat_input("What's up?"):
        # Display user message in chat message container
        write_message("user", prompt)

        # Generate a response
        handle_submit(prompt)
    # end::chat[]
