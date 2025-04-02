from typing import TypedDict

from langgraph.graph import add_messages
from typing_extensions import Annotated


class State(TypedDict):
    messages: Annotated[list, add_messages]
