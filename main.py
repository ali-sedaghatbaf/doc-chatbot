import asyncio
import os

import streamlit as st
from dotenv import load_dotenv

from adapters import doc
from src.adapters import wiki, wikipedia
from src.agent import graph_constructor, state_graph

load_dotenv()


async def construct_knowledge_graph(doc_name, doc_type):

    if doc_type == "Wikipedia":
        text = wikipedia.read_doc(doc_name)
    elif doc_type == "pdf":
        text = doc.read_doc(doc_name)
        doc_name = os.path.basename(doc_name)
    else:
        text = wiki.read_doc(doc_name)

    await graph_constructor.process_document(
        text, doc_name, chunk_size=500, chunk_overlap=100
    )


def answer_question(question):
    response = state_graph.sg_builder.invoke(
        {"question": question}, {"recursion_limit": 100, "thread_id": 1}
    )
    return response["answer"]


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
            ("Klarna Wiki", "Wikipedia"),
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
