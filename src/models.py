from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field, model_validator

from src.utils import encode_md5


class Polygon(BaseModel):
    p1: Tuple[float, float] = Field(..., description="First point (x1, y1)")
    p2: Tuple[float, float] = Field(..., description="Second point (x2, y2)")
    p3: Tuple[float, float] = Field(..., description="Third point (x3, y3)")
    p4: Tuple[float, float] = Field(..., description="Fourth point (x4, y4)")


class Block(BaseModel):
    block_id: str = Field(..., description="The id of the block")
    block_text: str = Field(..., description="The text of the block")
    block_type: Literal[
        "Line",
        "Span",
        "FigureGroup",
        "TableGroup",
        "ListGroup",
        "PictureGroup",
        "Page",
        "Caption",
        "Code",
        "Figure",
        "Footnote",
        "Form",
        "Equation",
        "Handwriting",
        "TextInlineMath",
        "ListItem",
        "PageFooter",
        "PageHeader",
        "Picture",
        "SectionHeader",
        "Table",
        "Text",
        "TableOfContents",
        "Document",
    ] = Field(..., description="The type of the block")
    block_position: List[int] = Field(..., description="The position of the block")


class Page(BaseModel):
    page_id: str = Field(..., description="The id of the page")
    page_number: int = Field(..., description="The page number of the page")
    page_blocks: List[Block] = Field(..., description="The blocks of the page")
    page_position: List[int] = Field(..., description="The position of the page")
    page_image: bytes = Field(..., description="The image of the page")


class Document(BaseModel):
    document_name: str = Field(..., description="The name of the document")
    document_address: str = Field(..., description="The address of the document")
    document_pages: List[Page] = Field(..., description="The pages of the document")
    document_metadata: Dict[str, Any] = Field(
        ..., description="The metadata of the document"
    )

    class Config:
        min_anystr_length = 1
        anystr_strip_whitespace = True


class AtomicFact(BaseModel):
    key_elements: List[str] = Field(
        description="""The essential nouns (e.g., characters, times, events, places, numbers), verbs (e.g.,
actions), and adjectives (e.g., states, feelings) that are pivotal to the atomic fact's narrative."""
    )
    atomic_fact: str = Field(
        description="""The smallest, indivisible facts, presented as concise sentences. These include
propositions, theories, existences, concepts, and implicit elements like logic, causality, event
sequences, interpersonal relationships, timelines, etc."""
    )
    id: Optional[str] = None

    @model_validator(mode="after")
    def set_id(self):
        if self.atomic_fact and not self.id:
            self.id = encode_md5(self.atomic_fact)


class Extraction(BaseModel):
    atomic_facts: List[AtomicFact] = Field(description="List of atomic facts")


class Node(BaseModel):
    key_element: str = Field(description="""Key element or name of a relevant node""")
    score: int = Field(
        description="""Relevance to the potential answer by assigning
    a score between 0 and 100. A score of 100 implies a high likelihood of relevance to the answer,
    whereas a score of 0 suggests minimal relevance."""
    )


class InitialNodes(BaseModel):
    initial_nodes: List[Node] = Field(
        description="List of relevant nodes to the question and plan"
    )


class AtomicFactOutput(BaseModel):
    updated_notebook: str = Field(
        description="""First, combine your current notebook with new insights and findings about
the question from current atomic facts, creating a more complete version of the notebook that
contains more valid information."""
    )
    rational_next_action: str = Field(
        description="""Based on the given question, the rational plan, previous actions, and
notebook content, analyze how to choose the next action."""
    )
    chosen_action: str = Field(
        description="""1. read_chunk(List[ID]): Choose this action if you believe that a text chunk linked to an atomic
fact may hold the necessary information to answer the question. This will allow you to access
more complete and detailed information.
2. stop_and_read_neighbor(): Choose this action if you ascertain that all text chunks lack valuable
information."""
    )


class ChunkOutput(BaseModel):
    updated_notebook: str = Field(
        description="""First, combine your previous notes with new insights and findings about the
    question from current text chunks, creating a more complete version of the notebook that contains
    more valid information."""
    )
    rational_next_move: str = Field(
        description="""Based on the given question, rational plan, previous actions, and
    notebook content, analyze how to choose the next action."""
    )
    chosen_action: str = Field(
        description="""1. search_more(): Choose this action if you think that the essential information necessary to
    answer the question is still lacking.
    2. read_previous_chunk(): Choose this action if you feel that the previous text chunk contains
    valuable information for answering the question.
    3. read_subsequent_chunk(): Choose this action if you feel that the subsequent text chunk contains
    valuable information for answering the question.
    4. termination(): Choose this action if you believe that the information you have currently obtained
    is enough to answer the question. This will allow you to summarize the gathered information and
    provide a final answer."""
    )


class NeighborOutput(BaseModel):
    rational_next_move: str = Field(
        description="""Based on the given question, rational plan, previous actions, and
    notebook content, analyze how to choose the next action."""
    )
    chosen_action: str = Field(
        description="""You have the following Action Options:
    1. read_neighbor_node(key element of node): Choose this action if you believe that any of the
    neighboring nodes may contain information relevant to the question. Note that you should focus
    on one neighbor node at a time.
    2. termination(): Choose this action if you believe that none of the neighboring nodes possess
    information that could answer the question."""
    )


class AnswerReasonOutput(BaseModel):
    analyze: str = Field(
        description="""You should first analyze each notebook content before providing a final answer.
        During the analysis, consider complementary information from other notes and employ a
    majority voting strategy to resolve any inconsistencies."""
    )
    final_answer: str = Field(
        description="""When generating the final answer, ensure that you take into account all available information."""
    )
