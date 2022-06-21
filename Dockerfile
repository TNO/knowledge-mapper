FROM python:3.10 AS builder

WORKDIR /usr/src/app/

RUN pip install --upgrade pip

# Install requirements in the Python environment.
COPY ./dev-requirements.txt .
RUN pip install -r dev-requirements.txt

COPY ./knowledge_mapper ./knowledge_mapper
COPY ./setup.py .
COPY ./MANIFEST.in .
COPY ./README.md .

RUN python setup.py sdist bdist_wheel

FROM python:3.10

WORKDIR /usr/src/app/

COPY --from=builder /usr/src/app/dist/*.whl .
RUN ls
RUN pip install ./*.whl

COPY  ./examples/sparql-mapper/config.json ./conf/config.json

ENTRYPOINT [ "python", "-m", "knowledge_mapper", "./conf/config.json" ]
