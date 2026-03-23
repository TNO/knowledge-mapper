from setuptools import find_packages, setup

setup(
    name="knowledge_mapper",
    version="0.1.0a0",
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
