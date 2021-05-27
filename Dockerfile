FROM python:3.9.5

WORKDIR /usr/src/app

# Install the requirements in the clean Python environment.
COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src

COPY ./default-config.json /usr/src/app/conf/config.json

CMD [ "python",  "./src/app.py", "./conf/config.json" ]
