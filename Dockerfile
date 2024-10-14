FROM python:3.13-alpine

ARG USER_UID="1000"
ARG USER_GID="1000"
ARG USER_NAME="datadog"
ARG USER_HOME="/home/datadog"

RUN apk --no-cache add ugrep=6.0.0-r0

RUN addgroup -g $USER_GID $USER_NAME && \
    adduser -G $USER_NAME -u $USER_UID -h $USER_HOME -D $USER_NAME

USER $USER_NAME
WORKDIR $USER_HOME

COPY --chown=$USER_NAME:$USER_NAME --chmod=0755 sniffer.py "$USER_HOME"

ENTRYPOINT ["./sniffer.py"]
