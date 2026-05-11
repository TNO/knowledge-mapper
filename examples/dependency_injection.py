"""Dependency injection example.

Demonstrates how to declare dependencies on handler functions using
``Depends()`` so that external resources (config, database connections,
HTTP clients, …) are injected by the framework at call time rather than
hard-coded as globals or closures.

Scenario: a KB that answers queries about sensor readings.  Two
dependencies are wired together:

  1. ``AppConfig`` — loaded once via ``get_config`` (cache=True, the
     default).
  2. ``SensorRepository`` — constructed from the config via
     ``get_sensor_repository``, which itself declares a ``Depends`` on
     ``get_config`` (transitive resolution).

Because both the handler and the repository factory depend on the same
``get_config`` factory, the config object is built only once per KI call.
"""

import sys
from pathlib import Path
from typing import Annotated

sys.path.insert(0, str(Path(__file__).parent))

from shared import get_example_logger

from src import Depends, KnowledgeBase
from src.ke.models import BindingModel, KnowledgeInteractionInfo, Literal, Uri

EXAMPLE_NAME = "dependency-injection"
logger = get_example_logger(EXAMPLE_NAME)

EX = "http://example.org/knowledge-mapper/dependency-injection#"

# ---------------------------------------------------------------------------
# Application-level resources
# ---------------------------------------------------------------------------


class AppConfig:
    """Holds application configuration."""

    def __init__(self, db_url: str = "sqlite:///sensors.db"):
        self.db_url = db_url


class SensorRepository:
    """A (fake) repository backed by a database connection."""

    # Static in-memory data for this example
    _READINGS: dict[str, float] = {
        f"{EX}sensor1": 21.3,
        f"{EX}sensor2": 19.8,
        f"{EX}sensor3": 22.7,
    }

    def __init__(self, db_url: str):
        self.db_url = db_url
        logger.debug("SensorRepository initialised (db_url=%s)", db_url)

    def get_reading(self, sensor_uri: str) -> float | None:
        return self._READINGS.get(sensor_uri)

    def all_readings(self) -> dict[str, float]:
        return dict(self._READINGS)


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------


def get_config() -> AppConfig:
    """Return the shared application config.

    In a real application this might load from environment variables or a
    config file.  With ``cache=True`` (the default) the framework calls this
    factory only once per KI call and reuses the result for every parameter
    that depends on it.
    """
    return AppConfig(db_url="sqlite:///sensors.db")


def get_sensor_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> SensorRepository:
    """Return a SensorRepository wired to the injected config.

    This factory itself declares a dependency on ``get_config``, demonstrating
    *transitive* (nested) resolution.  Because ``get_config`` uses
    ``cache=True``, the same ``AppConfig`` instance is reused here and in any
    other parameter of the same KI call that also depends on ``get_config``.
    """
    return SensorRepository(db_url=config.db_url)


# ---------------------------------------------------------------------------
# Binding model
# ---------------------------------------------------------------------------


class SensorReadingBinding(BindingModel):
    sensor: Uri
    temperature: Literal[float]


# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------

kb = KnowledgeBase(
    id=f"{EX}kb",
    name="dependency-injection-kb",
    description="A KB that demonstrates dependency injection via Depends().",
    ke_url="http://localhost:8280/rest",
)


@kb.answer_ki(
    name="sensor-readings-answer-ki",
    graph_pattern="""
        ?sensor a ex:Sensor ;
            ex:hasTemperature ?temperature .
    """,
    prefixes={"ex": EX},
)
def answer_sensor_readings(
    binding_set: list[SensorReadingBinding],
    info: KnowledgeInteractionInfo,
    repo: Annotated[SensorRepository, Depends(get_sensor_repository)],
    config: Annotated[AppConfig, Depends(get_config)],
) -> list[SensorReadingBinding]:
    """Answer queries about sensor temperatures.

    ``repo`` and ``config`` are injected by the framework.  Because
    ``get_config`` is ``cache=True``, the *same* ``AppConfig`` instance is
    passed to both ``get_sensor_repository`` and directly to this handler — it
    is constructed only once.

    ``binding_set`` may contain partial bindings (sensor URI provided,
    temperature unknown) or be empty (return all sensors).
    """
    logger.info(
        "Handling sensor-readings query (db=%s, incoming=%d bindings)",
        config.db_url,
        len(binding_set),
    )

    if binding_set:
        # Filtered query: only return the requested sensors
        results = []
        for b in binding_set:
            sensor_uri = str(b.sensor)
            temperature = repo.get_reading(sensor_uri)
            if temperature is not None:
                results.append(
                    SensorReadingBinding(sensor=b.sensor, temperature=temperature)
                )
        return results

    # Open query: return all known sensors
    return [
        SensorReadingBinding(sensor=uri, temperature=temp)  # type: ignore[arg-type]
        for uri, temp in repo.all_readings().items()
    ]


if __name__ == "__main__":
    kb.connect()
    kb.register()
    logger.info("Registered the dependency-injection example KB!")
    kb.start_handling_loop()
