FROM python:3.11.1-alpine

WORKDIR /usr/src/app/

RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# NOTE: In a real mapper you shouldn't copy the folder, but can simply add it to `requirements.txt`
COPY ./knowledge_mapper ./knowledge_mapper

# Place the configuration in the Docker image
COPY ./examples/sparql-mapper/config.jsonc .

ENTRYPOINT [ "python", "-m", "knowledge_mapper", "./config.jsonc" ]
