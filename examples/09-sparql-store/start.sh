#!/bin/sh

oxigraph_server load -f /start/data.ttl --location /data

exec oxigraph_server serve --bind 0.0.0.0:7878 --location /data
