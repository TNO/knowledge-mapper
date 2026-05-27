"""CLI example for the knowledge-mapper SDK.

In all previous examples, a KnowledgeBase was started directly from code, usually
registering in a main block. The SDK also provides a CLI that can be used to run a
KnowledgeBase from the command line, and automatically register and start handling
requests. Both are valid ways, you can choose based on your preferences and needs.

The CLI is based on Typer, and a basic usage is:
    knowledge-mapper run path/to/your_kb.py:kb
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared import get_example_logger

from knowledge_mapper import (
    BindingModel,
    KnowledgeBase,
    Literal,
    Uri,
)

EXAMPLE_NAME = "cli"
logger = get_example_logger(EXAMPLE_NAME)


# You build a KnowledgeBase as usual, defining interactions and binding models in code.
kb = KnowledgeBase(
    id="http://example.org/knowledge-mapper/cli#kb",
    name="CLI Example KB",
    description="A KB for demonstrating the CLI.",
    ke_url="http://localhost:8280/rest",
)


class EchoBinding(BindingModel):
    input: Uri
    value: Literal[str]


@kb.answer_ki(
    name="echo",
    graph_pattern="""
    ?input ex:hasValue ?value .
    """,
    prefixes={"ex": "http://example.org/knowledge-mapper/cli#"},
)
def echo_ki(binding_set: list[EchoBinding]) -> list[EchoBinding]:
    """A simple KI that echoes the input binding if all values are present."""
    return [b for b in binding_set if b.input and b.value]


# This example does not contain the "if __name__ == '__main__'" block that you might be
# used to from previous examples, because the CLI handles the entry point automatically.
