FROM python:latest
LABEL maintainer="dayt0n@dayt0n.com"
LABEL version="0.1"
LABEL description="anemoi is a self-hosted, secure dynamic DNS service"
WORKDIR /app
ADD anemoi anemoi
COPY setup.py .
RUN pip3 install .
ENTRYPOINT [ "anemoi" ]
