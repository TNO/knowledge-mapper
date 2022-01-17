from setuptools import setup

setup(
    name="knowledge_mapper",
    version="0.0.4",
    packages=["knowledge_mapper"],
    install_requires=["requests", "mysql-connector-python"],
    entry_points={
        "console_scripts": [
            "knowledge_mapper=knowledge_mapper.__main__:main",
        ]
    }
)
