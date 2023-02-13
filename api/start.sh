#!/bin/sh

python manage.py migrate

python manage.py createsuperuser --no-input

exec gunicorn km_backend.wsgi:application -b 0.0.0.0:8000
