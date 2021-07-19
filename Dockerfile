FROM python:3.9.5-alpine

WORKDIR /usr/src/app

RUN apk add --no-cache gcc musl-dev mariadb-connector-c-dev

# Install the requirements in the clean Python environment.
COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src

COPY ./conf/sparql-config.json /usr/src/app/conf/config.json

CMD [ "python",  "./src/app.py", "./conf/config.json" ]
