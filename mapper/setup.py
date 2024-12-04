from setuptools import setup, find_packages

setup(
    name="knowledge_mapper",
    version="0.0.24",
    packages=find_packages(),
    install_requires=[
        "requests",
        "mysql-connector-python",
        "json5",
        "websockets",
        "rdflib",
    ],
    entry_points={
        "console_scripts": [
            "knowledge_mapper=knowledge_mapper.__main__:main",
        ]
    },
)
