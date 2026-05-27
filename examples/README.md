# Knowledge Mapper Examples

The best way to get started with the Knowledge Mapper is by exploring the examples in this folder. Each example demonstrates a specific feature or pattern with detailed comments in the code.

## Overview

| Example | Description |
|---------|-------------|
| **01-basic.py** | A minimal knowledge base with a simple answer knowledge interaction |
| **02-binding_models.py** | Demonstrates using Pydantic-style binding models for type-safe bindings |
| **03-ask_interaction.py** | Shows how to handle ASK knowledge interactions |
| **04-post_measurement.py** | Demonstrates POST interactions for ingesting measurements or data |
| **05-custom-settings/** | Shows how to use custom settings to configure your knowledge mapper |
| **06-dependency_injection.py** | Uses dependency injection to inject resources like configs or database connections |
| **07-testing/** | Demonstrates how to write tests for your knowledge base using the fake client |

## Prerequisites

Before running the examples, you need to have a Knowledge Engine instance running. The examples expect it to be available at `http://localhost:8280/rest`.

### Starting the Knowledge Engine

Use the provided Docker Compose file to start a Knowledge Engine instance:

```bash
docker-compose up -d
```

This starts the Knowledge Engine and related services in the background. To stop them:

```bash
docker-compose down
```

## Running Examples

### Installation

First, install the knowledge mapper in your Python environment:

```bash
pip install knowledge_mapper
```

Or, if you're developing locally, install it in editable mode from the project root:

```bash
pip install -e .
```

### Running a Single Example

To run an example, navigate to the examples folder and execute the Python script:

```bash
cd examples
python 01-basic.py
```

Most examples will start the knowledge mapper and connect to the Knowledge Engine. Press `Ctrl+C` to stop.

### Running Tests

The `07-testing/` example includes test examples. Run them with:

```bash
python -m pytest 07-testing/
```

## Next Steps

1. Start with **01-basic.py** to understand the minimal setup
2. Explore **02-binding_models.py** to learn about type-safe bindings
3. Look at **03-ask_interaction.py** and **04-post_measurement.py** to see different KI types
4. Check **05-custom-settings/** for configuration patterns
5. Study **06-dependency_injection.py** to see how to manage dependencies
6. Review **07-testing/** to learn testing strategies

## Tips

- Each example has inline comments explaining the code
- The `shared.py` module contains utilities used by examples (like logging setup)
- To see detailed logs, check the output when running examples
- The examples use `http://localhost:8280/rest` as the default Knowledge Engine endpoint
