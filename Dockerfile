FROM python:3.13-slim

MAINTAINER Manuel Alvarez Alvarez "manuel.alvarezalvarez@datadoghq.com"

ARG USER_UID="1000"
ARG USER_GID="1000"
ARG USER_NAME="datadog"
ARG USER_HOME="/home/datadog"

RUN apt-get update && \
    apt-get install -y ugrep=3.11.2+dfsg-1 && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/*

RUN groupadd -g $USER_GID $USER_NAME && \
    useradd -m -g $USER_GID -u $USER_UID -d $USER_HOME $USER_NAME

USER $USER_NAME
WORKDIR $USER_HOME

COPY --chown=$USER_NAME:$USER_NAME --chmod=0755 sniffer.py "$USER_HOME"

ENTRYPOINT ["./sniffer.py"]
