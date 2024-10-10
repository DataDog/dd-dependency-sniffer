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


class Type(Enum):
    MAVEN = "maven"
    GRADLE = "gradle"

    def __str__(self):
        return self.value


@dataclass
class Dependency:
    groupId: str
    artifactId: str
    version: str
    scope: str
    type: str

    def __init__(
        self,
        groupId: str,
        artifactId: str,
        version: str,
        scope: str = None,
        type: str = "jar",
    ):
        self.groupId = groupId
        self.artifactId = artifactId
        self.version = version
        self.scope = scope
        self.type = type

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.groupId == other.groupId
                and self.artifactId == other.artifactId
                and self.version == other.version
            )
        else:
            return False

    def __hash__(self):
        return hash((self.groupId, self.artifactId, self.version))

    def __str__(self):
        return f"{self.groupId}:{self.artifactId}:{self.version}"


def _analyze_java_dependencies(args: Namespace):
    """Searches the workspace for Java dependencies"""
    if args.package is not None:
        message = f"The package with name '{args.package}' has been referenced in the following files: "
        result = _find_java_packages(args)
    elif args.artifact is not None:
        message = f"The artifact with id '{args.artifact}' has been referenced in the following files: "
        result = _find_java_artifact(args)
    else:
        raise RuntimeError(
            "You have to specify either --package or --coordinates to discover dependencies"
        )
    print(message)
    dependencies = dict()
    for item in result:
        index = item.index("{")
        parent_file = item[0:index]
        children_ref = item[index + 1 : -1]
        if parent_file not in dependencies:
            children = []
            dependencies[parent_file] = children
        else:
            children = dependencies[parent_file]

        match len(children):
            case x if x < 3:
                children.append(children_ref)
            case x if x == 3:
                children.append("...")

    print(json.dumps(dependencies, sort_keys=True, indent=4))


def _find_java_packages(args: Namespace) -> list[str]:
    """Finds java binaries with the selected package in the bytecode and makes sure it's the original class and not a reference"""
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

    if result.returncode != 0:
        error = result.stderr.decode()
        raise RuntimeError(error)

    matches = json.loads(result.stdout)
    return [
        match["file"].replace(args.workspace, "")
        for match in matches
        if match["file"].find(vm_package) >= 0
    ]


def _find_java_artifact(args: Namespace) -> list[str]:
    """Tries to find the selected artifactId in internal files like pom.xml"""
    result = subprocess.run(
        [
            "ug",
            "-r",  # recurse
            "-z",
            f"--zmax={args.depth}",  # decompress files
            "-o",  # only output the match
            "-%",
            f"artifactId={args.artifact}",  # containing the artifact description
            "--json",
            args.workspace,
        ],
        capture_output=True,
    )

    if result.returncode != 0:
        error = result.stderr.decode()
        raise RuntimeError(error)

    matches = json.loads(result.stdout)
    return [match["file"].replace(args.workspace, "") for match in matches]


def _copy_java_dependencies(args: Namespace, dependencies: set[Dependency]):
    """Copies the selected dependencies into the workspace for further analysis, it first tries the maven home and then switches to the gradle one"""
    if not os.path.exists(args.workspace):
        os.makedirs(args.workspace)

    home = os.environ.get("HOME")
    maven_home = os.path.join(home, ".m2", "repository")
    gradle_home = os.path.join(home, ".gradle", "caches", "modules-2", "files-2.1")

    if not os.path.exists(args.workspace):
        raise RuntimeError(
            "Missing maven home, are you setting the M2_HOME variable properly?"
        )

    for dep in dependencies:
        if not _copy_java_dependency(dep, maven_home, gradle_home, args.workspace):
            print(
                f"Missing dependency {dep}",
                file=sys.stderr,
            )


def _copy_java_dependency(
    dep: Dependency, maven_home: str, gradle_home: str, target: str
) -> bool:
    if _copy_maven_dependency(dep, maven_home, target):
        return True

    if _copy_gradle_dependency(dep, gradle_home, target):
        return True

    return _copy_maven_central_dependency(dep, target)


def _copy_maven_dependency(dep: Dependency, maven_home: str, target: str) -> bool:
    group_path = reduce(
        lambda result, item: os.path.join(result, item),
        dep.groupId.split("."),
        maven_home,
    )
    version_path = os.path.join(group_path, dep.artifactId, dep.version)
    file_name = f"{dep.artifactId}-{dep.version}.{dep.type}"
    artifact_path = os.path.join(version_path, file_name)
    if not os.path.exists(artifact_path):
        return False
    else:
        shutil.copyfile(
            artifact_path,
            os.path.join(target, file_name),
            follow_symlinks=True,
        )
        return True


def _copy_gradle_dependency(dep: Dependency, gradle_home: str, target: str) -> bool:
    version_path = os.path.join(gradle_home, dep.groupId, dep.artifactId, dep.version)
    if not os.path.exists(version_path):
        return False
    file_name = f"{dep.artifactId}-{dep.version}.{dep.type}"
    path = Path(version_path)
    artifact_path = None
    for f in path.iterdir():
        final_path = os.path.join(f, file_name)
        if f.is_dir() and os.path.isfile(final_path):
            artifact_path = final_path
            break

    if artifact_path is None:
        return False
    else:
        shutil.copyfile(
            artifact_path,
            os.path.join(target, file_name),
            follow_symlinks=True,
        )


def _copy_maven_central_dependency(dep: Dependency, target: str) -> bool:
    local_file = os.path.join(target, f"{dep.artifactId}-{dep.version}.{dep.type}")
    group = dep.groupId.replace(".", "/")
    url = f"https://repo1.maven.org/maven2/{group}/{dep.artifactId}/{dep.version}/{dep.artifactId}-{dep.version}.{dep.type}"
    try:
        with urllib.request.urlopen(url) as remote, open(local_file, "wb") as local:
            if remote.code == 200:
                local.write(remote.read())
                return True
            else:
                return False
    except Exception as e:
        return False


def _extract_maven_dependencies(args: Namespace) -> set[Dependency]:
    """Extracts the different Maven coordinates from a dependency tree in JSON format"""
    source = args.source
    if not os.path.isfile(source):
        raise ValueError(
            f"{source} must be set to a file containing a Maven dependency tree export"
        )

    dependencies = set()
    json_deps = []
    with open(source, "r") as target:
        try:
            parsed = json.load(target)
        except Exception as err:
            raise RuntimeError("Failed to parse Maven json dependency tree", err)
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
    source = args.source
    if not os.path.isfile(source):
        raise ValueError(
            f"{source} must be set to a file containing a Gradle dependency tree export"
        )

    dependencies = set()
    with open(source, "r") as target:
        for line in target:
            match = re.search(r"[+\\]--- (\S+:\S+:\S+)", line)
            if match is not None:
                group, artifact, version = match.group(1).split(":")
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--type",
        help="Type of analyzer for the dependencies",
        type=Type,
        choices=list(Type),
    )
    parser.add_argument(
        "--depth",
        help="Max recursive depth to search in compressed files",
        type=int,
        default=10,
    )
    parser.add_argument(
        "--package", help="Name of the package to search in the dependencies", type=str
    )
    parser.add_argument(
        "--artifact", help="Artifact id for the maven coordinates", type=str
    )
    parser.add_argument(
        "--workspace",
        help="source folder to store all dependencies",
        type=str,
        default="/home/datadog/workspace",
    )
    parser.add_argument(
        "source",
        help="source files for the analysis",
        type=str,
        nargs="?",
        default="/home/datadog/source",
    )
    args = parser.parse_args()

    match args.type:
        case Type.MAVEN:
            _analyze_maven(args)
        case Type.GRADLE:
            _analyze_gradle(args)
        case _:
            raise ValueError(f"Wrong type selected: {args.type}")


analyze()
