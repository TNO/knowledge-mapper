FROM python:3.9.7-bullseye

WORKDIR /usr/src/app

# Install the requirements in the clean Python environment.
COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app.py .
COPY ./knowledge_mapper ./knowledge_mapper

COPY ./conf/sparql-config.json ./conf/config.json

CMD [ "python",  "./app.py", "./conf/config.json" ]
