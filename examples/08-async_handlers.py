"""Async REACT handlers example.

Demonstrates two REACT handlers in one KB:
1) a sync handler (``def``)
2) an async handler (``async def``)

The comments highlight how the mapper executes each style differently.
"""

import asyncio
import time

from shared import get_example_logger

from knowledge_mapper import (
    BindingModel,
    KnowledgeBase,
    KnowledgeInteractionInfo,
    Literal,
    Uri,
)

EXAMPLE_NAME = "async-handlers"
logger = get_example_logger(EXAMPLE_NAME)

EX = "http://example.org/knowledge-mapper/async-handlers#"


class DeviceCommandBinding(BindingModel):
    device: Uri
    desired_state: Literal[str]


class DeviceAckBinding(BindingModel):
    device: Uri
    accepted: Literal[bool]
    source: Literal[str]


kb = KnowledgeBase(
    id=f"{EX}kb",
    name="async-handlers-kb",
    description="A KB that demonstrates async vs sync REACT handlers.",
    ke_url="http://localhost:8280/rest",
)


@kb.react_ki(
    name="device-react-sync-ki",
    argument_graph_pattern="""
        ?device a ex:Device ;
            ex:desiredState ?desiredState .
    """,
    result_graph_pattern="""
        ?device ex:accepted ?accepted ;
            ex:handledBy ?source .
    """,
    prefixes={"ex": EX},
)
def react_device_sync(
    binding_set: list[DeviceCommandBinding],
    info: KnowledgeInteractionInfo,
) -> list[DeviceAckBinding]:
    # Sync handlers are executed with asyncio.to_thread(...).
    # That keeps the event loop responsive, but this function itself still blocks
    # the worker thread while it runs.
    time.sleep(4)
    return [
        DeviceAckBinding(device=b.device, accepted=True, source="sync-handler")
        for b in binding_set
    ]


@kb.react_ki(
    name="device-react-async-ki",
    argument_graph_pattern="""
        ?device a ex:Device ;
            ex:desiredState ?desiredState .
    """,
    result_graph_pattern="""
        ?device ex:accepted ?accepted ;
            ex:handledBy ?source .
    """,
    prefixes={"ex": EX},
)
async def react_device_async(
    binding_set: list[DeviceCommandBinding],
    info: KnowledgeInteractionInfo,
) -> list[DeviceAckBinding]:
    # Async handlers are awaited directly on the event loop.
    # Use this style when the handler performs awaitable I/O (HTTP calls, DB
    # drivers, message brokers, etc.) so multiple requests can overlap.
    await asyncio.sleep(4)
    return [
        DeviceAckBinding(device=b.device, accepted=True, source="async-handler")
        for b in binding_set
    ]


async def main():
    await kb.connect()
    await kb.register()
    logger.info("KB registered.")

    # In real usage, REACT handlers are triggered by incoming POST interactions
    # from the KE. Here we call them locally via kb.call(...) to make behavior
    # easy to observe in a standalone script.
    incoming = [
        {
            "device": f"<{EX}device-1>",
            "desiredState": '"on"',
        }
    ]

    sync_result = await kb.call(incoming, "device-react-sync-ki")
    logger.info("Sync REACT result: %s", sync_result)

    async_result = await kb.call(incoming, "device-react-async-ki")
    logger.info("Async REACT result: %s", async_result)

    await kb.unregister()
    logger.info("KB unregistered.")


if __name__ == "__main__":
    asyncio.run(main())
