"""Dockerized example: a one-shot ASK knowledge base that queries ``app.py``.

Runs from the same image as the answering KB (see compose.yaml) to show that the
dockerized KB is reachable on the knowledge network. It asks once, logs the
answers, unregisters and exits.

Configured through the same environment variables as ``app.py``.
"""

import asyncio
import logging

from knowledge_mapper import KnowledgeBase, KnowledgeBaseSettings

logger = logging.getLogger("dockerized-asker")
_handler = logging.StreamHandler()
_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] [dockerized-asker] %(message)s")
)
logger.addHandler(_handler)
logger.setLevel(logging.INFO)

ATTEMPTS = 30
RETRY_DELAY_SECONDS = 2

settings = KnowledgeBaseSettings()  # type: ignore[call-arg]
kb = KnowledgeBase.from_settings(settings).build()

kb.ask_ki(
    name="greeting-ask-ki",
    graph_pattern="""
        ?greeting a ex:Greeting ;
            ex:hasText ?text .
    """,
    prefixes={"ex": "http://example.org/knowledge-mapper/dockerized#"},
)


async def wait_for_smart_connector() -> None:
    for _ in range(ATTEMPTS):
        try:
            await kb.connect()
            return
        except Exception as error:
            logger.info(f"Smart Connector not ready yet ({error}), retrying...")
            await asyncio.sleep(RETRY_DELAY_SECONDS)
    raise RuntimeError("Smart Connector did not become available.")


async def main() -> None:
    await wait_for_smart_connector()
    await kb.register()
    try:
        # The answering KB may still be starting, so retry until it answers.
        for _ in range(ATTEMPTS):
            result = await kb.ask([], "greeting-ask-ki")
            if result:
                for binding in result:
                    logger.info(f"Received answer: {binding}")
                return
            logger.info("No answers yet, retrying...")
            await asyncio.sleep(RETRY_DELAY_SECONDS)
        raise RuntimeError("No knowledge base answered the greeting request.")
    finally:
        await kb.unregister()
        await kb.close()


if __name__ == "__main__":
    asyncio.run(main())
