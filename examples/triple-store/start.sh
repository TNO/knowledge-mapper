#!/bin/sh

oxigraph_server load -f /seed-data/data.ttl --location /data

exec oxigraph_server serve --bind 0.0.0.0:7878 --location /data
