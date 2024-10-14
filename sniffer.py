#!/usr/bin/env python3

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from argparse import Namespace
from dataclasses import dataclass
from enum import Enum
from functools import reduce
from pathlib import Path
from urllib.error import URLError


class Type(Enum):
    MAVEN = "maven"
    GRADLE = "gradle"

    def __str__(self):
        return self.value


@dataclass
class Dependency:
    group_id: str
    artifact_id: str
    version: str
    scope: str
    type: str

    def __init__(
        self,
        group_id: str,
        artifact_id: str,
        version: str,
        scope: str = None,
        type: str = "jar",
    ):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.version = version
        self.scope = scope
        self.type = type

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.group_id == other.group_id
                and self.artifact_id == other.artifact_id
                and self.version == other.version
            )

    def __hash__(self):
        return hash((self.group_id, self.artifact_id, self.version))

    def __str__(self):
        return f"{self.group_id}:{self.artifact_id}:{self.version}"


def _analyze_java_dependencies(args: Namespace):
    """Performs a search in the files contained in the workspace using the provided filter"""
    if args.package is not None:
        message = f"The package with name '{args.package}'"
        result = _find_java_packages(args)
    elif args.artifact is not None:
        message = f"The artifact with id '{args.artifact}'"
        result = _find_java_artifact(args)
    else:
        print("You have to specify either --package or --artifact", file=sys.stderr)
        exit(1)

    if len(result) == 0:
        print(message + " has not been found in any file(s)")
    else:
        print(message + " has been found in the following file(s):")
        dependencies = dict()
        for item in result:
            index = item.index("{")
            parent_file = item[len(args.workspace) + 1: index]
            children_ref = item[index + 1: -1]
            children = dependencies.setdefault(parent_file, [])
            match len(children):
                case x if x < 3:
                    children.append(children_ref)
                case x if x == 3:
                    children.append("...")

        print(json.dumps(dependencies, sort_keys=True, indent=4))


def _find_java_packages(args: Namespace) -> list[str]:
    """Finds java binaries with the selected package name in the bytecode and makes sure it's the original class and
    not a reference"""
    vm_package = args.package.replace(".", "/")
    result = subprocess.run(
        [
            "ug",
            "-r",  # recurse
            "-z",
            f"--zmax={args.depth}",  # decompress files
            "-o",  # only output the match
            "-e",
            f"{vm_package}",  # containing the package declaration
            "--json",
            args.workspace,
        ],
        capture_output=True,
    )

    if len(result.stderr) > 0:
        error = result.stderr.decode()
        raise RuntimeError(error)

    matches = json.loads(result.stdout)
    vm_package_regexp = r"\b" + re.escape(vm_package)
    return [match["file"] for match in matches if re.search(vm_package_regexp, match["file"])]


def _find_java_artifact(args: Namespace) -> list[str]:
    """Finds internal files like pom.xml, MANIFEST.MF containing the selected artifact"""
    result = subprocess.run(
        [
            "ug",
            "-r",  # recurse
            "-z",
            f"--zmax={args.depth}",  # decompress files
            "-o",  # only output the match
            "-%",
            f"artifactId={args.artifact} OR Implementation-Title:.+{args.artifact} OR Bundle-.*Name:.+{args.artifact}",
            # containing the artifact description
            "--json",
            args.workspace,
        ],
        capture_output=True,
    )

    if len(result.stderr) > 0:
        error = result.stderr.decode()
        raise RuntimeError(error)

    matches = json.loads(result.stdout)
    return [match["file"] for match in matches]


def _copy_java_dependencies(args: Namespace, dependencies: set[Dependency]):
    """Copies the selected dependencies into the workspace for further analysis"""
    if not os.path.exists(args.workspace):
        os.makedirs(args.workspace)
    else:
        for root, dirs, files in os.walk(args.workspace):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))

    home = os.environ.get("HOME")
    maven_home = os.path.join(home, ".m2", "repository")
    gradle_home = os.path.join(home, ".gradle", "caches", "modules-2", "files-2.1")

    for dep in dependencies:
        if not _copy_java_dependency(dep, maven_home, gradle_home, args.workspace):
            print(
                f"Cannot find dependency with coordinates '{dep}'",
                file=sys.stderr,
            )


def _copy_java_dependency(
    dep: Dependency, maven_home: str, gradle_home: str, target: str
) -> bool:
    """Copies the selected dependency into the workspace, it first tries maven, then gradle and finally tries to
    resolve the dependency against maven central"""
    if os.path.exists(maven_home) and _copy_maven_dependency(dep, maven_home, target):
        return True

    if os.path.exists(gradle_home) and _copy_gradle_dependency(
        dep, gradle_home, target
    ):
        return True

    return _copy_maven_central_dependency(dep, target)


def _copy_maven_dependency(dep: Dependency, maven_home: str, target: str) -> bool:
    group_path = reduce(
        lambda result, item: os.path.join(result, item),
        dep.group_id.split("."),
        maven_home,
    )
    version_path = os.path.join(group_path, dep.artifact_id, dep.version)
    file_name = f"{dep.artifact_id}-{dep.version}.{dep.type}"
    artifact_path = os.path.join(version_path, file_name)
    if os.path.exists(artifact_path):
        shutil.copyfile(
            artifact_path,
            os.path.join(target, file_name),
            follow_symlinks=True,
        )
        return True


def _copy_gradle_dependency(dep: Dependency, gradle_home: str, target: str) -> bool:
    version_path = os.path.join(gradle_home, dep.group_id, dep.artifact_id, dep.version)
    if not os.path.exists(version_path):
        return False
    file_name = f"{dep.artifact_id}-{dep.version}.{dep.type}"
    path = Path(version_path)
    artifact_path = None
    for f in path.iterdir():
        final_path = os.path.join(f, file_name)
        if f.is_dir() and os.path.isfile(final_path):
            artifact_path = final_path
            break

    if artifact_path is not None:
        shutil.copyfile(
            artifact_path,
            os.path.join(target, file_name),
            follow_symlinks=True,
        )
        return True


def _copy_maven_central_dependency(dep: Dependency, target: str) -> bool:
    local_file = os.path.join(target, f"{dep.artifact_id}-{dep.version}.{dep.type}")
    group = dep.group_id.replace(".", "/")
    url = f"https://repo1.maven.org/maven2/{group}/{dep.artifact_id}/{dep.version}/{dep.artifact_id}-{dep.version}.{dep.type}"
    try:
        with urllib.request.urlopen(url) as remote, open(local_file, "wb") as local:
            if remote.code != 200:
                return False
            local.write(remote.read())
            return True
    except URLError:
        return False


def _extract_maven_dependencies(args: Namespace) -> set[Dependency]:
    """Extracts the different Maven coordinates from a dependency tree in JSON format"""
    input_file = args.input
    if not os.path.isfile(input_file):
        print("The Maven dependency report file does not exist", file=sys.stderr)
        exit(1)

    dependencies = set()
    json_deps = list()
    with open(input_file) as target:
        try:
            parsed = json.load(target)
        except Exception as err:
            print("Failed to parse Maven json dependency tree", file=sys.stderr)
            exit(1)
        if isinstance(parsed, list):
            json_deps.extend(parsed)
        else:
            json_deps.append(parsed)

    while len(json_deps) > 0:
        dep = json_deps.pop(0)
        dependencies.add(
            Dependency(
                dep["groupId"],
                dep["artifactId"],
                dep["version"],
                dep["scope"],
                dep["type"],
            )
        )
        if "children" in dep:
            json_deps.extend(dep["children"])

    return dependencies


def _extract_gradle_dependencies(args: Namespace) -> set[Dependency]:
    """Extracts the different Gradle coordinates from a dependency tree in textual format"""
    input_file = args.input
    if not os.path.isfile(input_file):
        print("The Gradle dependency report file does not exist", file=sys.stderr)
        exit(1)

    dependencies = set()
    with open(input_file) as target:
        for line in target:
            match = re.search(r"[+\\]--- (\S+:\S+:.+$)", line)
            if match is not None:
                group, artifact, version = match.group(1).split(":")
                version = re.sub(r" \(.+\)", "", version)
                index = version.find(" -> ")
                if index >= 0:
                    version = version[index + 4:]
                dependencies.add(Dependency(group, artifact, version))

    return dependencies


def _analyze_maven(args: Namespace):
    """Picks up a Maven dependency tree in JSON and fetches the dependencies"""
    dependencies = _extract_maven_dependencies(args)
    _copy_java_dependencies(args, dependencies)
    _analyze_java_dependencies(args)


def _analyze_gradle(args: Namespace):
    """Picks up a Gradle dependency tree in text format and fetches the dependencies"""
    dependencies = _extract_gradle_dependencies(args)
    _copy_java_dependencies(args, dependencies)
    _analyze_java_dependencies(args)


def analyze():
    """Parses the arguments provided via the CLI and calls the concrete analyze method."""
    parser = argparse.ArgumentParser(prog="run.sh")
    parser.add_argument(
        "--type",
        help="Build system handling the project",
        type=Type,
        choices=list(Type),
        required=True,
    )
    parser.add_argument(
        "--package", help="Package name prefix", type=str
    )
    parser.add_argument(
        "--artifact",
        help="Artifact id of the maven coordinates",
        type=str,
    )
    parser.add_argument(
        "input",
        help="Input file that will be analyzed by the sniffer",
        type=str,
        nargs="?",
        default="/home/datadog/input",
    )
    parser.add_argument(
        "--depth",
        help="(Optional) Max recursive depth to search in compressed files (default: 10)",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--workspace",
        help="(Optional) Temporary folder to store project dependencies",
        type=str,
        default="/home/datadog/workspace",
    )
    args = parser.parse_args()

    match args.type:
        case Type.MAVEN:
            _analyze_maven(args)
        case Type.GRADLE:
            _analyze_gradle(args)
        case _:
            print(f"Invalid type selected: {args.type}", file=sys.stderr)
            exit(1)


analyze()
