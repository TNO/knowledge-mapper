# Knowledge Mapper

This mapper makes it easier to disclose data from knowledge bases that use SPARQL and (future work) other protocols to a knowledge network.

## Where does it operate?

Given the configuration of your mappings, it talks to the knowledge engine's REST API to register the relevant knowledge interactions.

When there is an incoming request from the knowledge network (through the REST API), the mapper uses the configuration to retrieve the knowledge from the knowledge base.

## How to use it?

We publish releases of the knowledge mapper as Docker images.
Configuration goes into a file `/usr/src/app/conf/config.json` in that image.
You can mount a Docker volume at `/usr/src/app/conf`, and put your own `config.json` there, or overwrite `/usr/src/app/conf/config.json` in your own image.
