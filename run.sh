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

test_command "docker" "follow the guide at https://docs.docker.com/engine/install/"

if [ -f "$BASEDIR/Dockerfile" ]; then
  echo "Building docker image"
  docker build --quiet -t "$DOCKER_IMAGE" .
fi

args=()
type=""
source=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --type)
      type="$2"
      args+=("$1")
      args+=("$2")
      shift
      shift
      ;;
    -h|--help)
      args+=("$1")
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
      shift
      ;;
  esac
done

cmd="docker run --rm"

# mount the source pointing to the dependencies
if [ -n "$source" ]; then
  args+=("/home/datadog/source")
  cmd="$cmd -v $source:/home/datadog/source"
fi

# mount maven home if available
if [ ! -d "$M2_HOME" ]; then
  if [ "$type" == "maven" ]; then
    echo "Current env M2_HOME=$M2_HOME does not point to a valid folder, try defining a different value"
  fi
else
  cmd="$cmd -v $M2_HOME:/home/datadog/.m2"
fi

# mount gradle home if available
if [ ! -d "$GRADLE_USER_HOME" ]; then
  if [[ $type == "gradle" ]]; then
    echo "Current env GRADLE_USER_HOME=$GRADLE_USER_HOME does not point to a valid folder, try defining a different value"
  fi
else
  cmd="$cmd -v $GRADLE_USER_HOME:/home/datadog/.gradle"
fi

cmd="$cmd $DOCKER_IMAGE ${args[*]}"

echo "Analyzing dependencies"
eval "$cmd"
exit "$?";
