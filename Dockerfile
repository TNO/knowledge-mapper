FROM python:3.10

WORKDIR /usr/src/app/

RUN pip install --upgrade pip

# Install requirements in the Python environment.
COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./knowledge_mapper ./knowledge_mapper

COPY  ./examples/sparql-mapper/config.json ./conf/config.json

ENTRYPOINT [ "python", "-m", "knowledge_mapper", "./conf/config.json" ]
