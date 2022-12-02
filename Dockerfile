# syntax=docker/dockerfile:1
FROM python:3.8-slim-buster

# Require a "GIT_SHA" argument to be passed using `--build-arg GIT_SHA=...".
# Then, make the value available as an environment variable in the container.
ARG GIT_SHA
RUN echo "${GIT_SHA}" | grep -e "[0-9a-f]\{40\}"
ENV GIT_SHA="$GIT_SHA"

ENV PIP_DISABLE_PIP_VERSION_CHECK=on

RUN apt-get update && apt-get install -y --no-install-recommends \
    # application requirements:
    build-essential gcc make libpq-dev \
    # deployment requirements:
    openssl \
    # python/poetry setup:
    && python3 -m pip install poetry

# generate self-signed certs for our API
RUN openssl genrsa -out /etc/ssl/private/gunicorn.key 2048 \
    && openssl req -new -key /etc/ssl/private/gunicorn.key -out /etc/ssl/certs/gunicorn.csr -subj '/C=/ST=/L=/O=globus.org/OU=globus-flows/CN=gunicorn' \
    && openssl x509 -req -days 365 -in /etc/ssl/certs/gunicorn.csr -signkey /etc/ssl/private/gunicorn.key -out /etc/ssl/certs/gunicorn.crt


WORKDIR /app

COPY Makefile pyproject.toml poetry.lock poetry.toml README.md LICENSE app.py ./
COPY provider provider

RUN python -m pip install "gunicorn>=20.0,<21.0"

RUN \
    set -eu; \
    poetry install --no-dev; \
    poetry cache clear --all --no-interaction pypi;

CMD ["gunicorn"  , "-b", "0.0.0.0:8000", "app:app"]


EXPOSE 8000