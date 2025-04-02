from operator import add
from typing import List

from typing_extensions import Annotated, TypedDict


class InputState(TypedDict):
    question: str


class OutputState(TypedDict):
    answer: str
    analysis: str
    previous_actions: List[str]
    citations: List[str]


class OverallState(TypedDict):
    question: str
    rational_plan: str
    notebook: str
    previous_actions: Annotated[List[str], add]
    context: List[str]
    check_atomic_facts_queue: List[str]
    check_chunks_queue: List[str]
    neighbor_check_queue: List[str]
    chosen_action: str
