#!/bin/bash

set -eu

BASEDIR=$(dirname "$0")
DOCKER_IMAGE=${DOCKER_IMAGE:-ghcr.io/datadog/dd-dependency-sniffer:latest}
M2_HOME=${M2_HOME:-"$HOME"/.m2}
GRADLE_USER_HOME=${GRADLE_USER_HOME:-"$HOME"/.gradle}

test_command() {
    if ! command -v "$1" >/dev/null 2>&1
    then
        echo "$1 could not be found, $2"
        exit 1
    fi
}

test_command "docker" "Follow the guide at https://docs.docker.com/engine/install/"

if [ -f "$BASEDIR/Dockerfile" ]; then
  docker_log=$(mktemp)
  docker build -t "$DOCKER_IMAGE" . > "$docker_log" 2>&1
  if [ $? != 0 ]; then
    echo "Failed to build docker image, check logs at $docker_log"
    exit 1
  fi
fi

args=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --type)
      type="$2"
      args+=("$1")
      args+=("$2")
      shift
      shift
      ;;
    --*)
      args+=("$1")
      args+=("$2")
      shift
      shift
      ;;
    *)
      source="$1"
      args+=("/home/datadog/source") # mounted value
      shift
      ;;
  esac
done

cmd="docker run --rm -v $source:/home/datadog/source"
# mount maven home if available
if [ ! -d "$M2_HOME" ]; then
  if [ "$type" == "maven" ]; then
    echo "Current env M2_HOME=$M2_HOME does not point to a valid folder, try defining a different value"
    exit 1
  fi
else
  cmd="$cmd -v $M2_HOME:/home/datadog/.m2"
fi

# mount gradle home if available
if [ ! -d "$GRADLE_USER_HOME" ]; then
  if [[ $type == "gradle" ]]; then
    echo "Current env GRADLE_USER_HOME=$GRADLE_USER_HOME does not point to a valid folder, try defining a different value"
    exit 1
  fi
else
  cmd="$cmd -v $GRADLE_USER_HOME:/home/datadog/.gradle"
fi

cmd="$cmd $DOCKER_IMAGE ${args[*]}"
eval "$cmd"

exit 0;