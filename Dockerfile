FROM python:3.9.8-bullseye

WORKDIR /usr/src/app

# Install the requirements in the clean Python environment.
COPY ./requirements.txt .

RUN python -m venv venv
ENV PATH="/usr/src/app/venv/bin:$PATH"

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app.py .
COPY ./knowledge_mapper ./knowledge_mapper

COPY ./conf/sparql-kb-config.json ./conf/config.json

CMD [ "python",  "./app.py", "./conf/config.json" ]
