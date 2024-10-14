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

print_usage() {
  echo "$1"
  docker run --rm "$DOCKER_IMAGE" --help
  exit 1
}

test_command "docker" "follow the guide at https://docs.docker.com/engine/install/"

if [ -f "$BASEDIR/Dockerfile" ]; then
  echo "Building docker image"
  docker build --quiet -t "$DOCKER_IMAGE" .
fi

args=()
type=""
input=""
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
      input=$(realpath "$1")
      shift
      ;;
  esac
done

cmd="docker run --rm"

# mount the source pointing to the dependencies
if [ -z "$input" ]; then
  print_usage "Missing positional argument 'input'"
else
  if [ ! -f "$input" ]; then
    echo "Cannot find $input, review the actual path to the report"
    exit 1
  fi
  args+=("/home/datadog/input")
  cmd="$cmd -v $input:/home/datadog/input"
fi

if [ -z "$type" ]; then
  print_usage "Missing option '--type'"
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

echo "Analyzing '$type' dependencies in '$input'"
stderr=$(mktemp dd-dependency-sniffer.XXX.err)
eval "$cmd" 2>"$stderr"
if [ -s "$stderr" ]; then
  >&2 echo "The log file '$stderr' has been generated with all the error output from the process"
else
   rm "$stderr"
fi

exit 0;
