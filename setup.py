from setuptools import setup

setup(
    name="knowledge_mapper",
    version="0.0.9",
    packages=["knowledge_mapper"],
    install_requires=["requests", "mysql-connector-python", "pyjson5"],
    entry_points={
        "console_scripts": [
            "knowledge_mapper=knowledge_mapper.__main__:main",
        ]
    }
)
