# Datadog dependency sniffer

This repository contains a utility script that can help troubleshoot finding the exact location of vulnerable
dependencies that form part of a project.

## Introduction

Most of the time the dependencies used to build a project are easy to locate as they are direct or transitive, most of
the tooling used to build a project offer utilities to list them properly (
e.g.: [maven](https://maven.apache.org/plugins/maven-dependency-plugin/tree-mojo.html), [gradle](https://docs.gradle.org/current/userguide/viewing_debugging_dependencies.html)).

In other cases finding the actual location of the dependency is way harder due to dependency shading and relocation:

* **Shading**: when a dependency is shaded, it's packaged inside another dependency and the transitive relation is lost
  from the package manager point of view.
* **Relocation**: is the same as shading plus changing the actual package/namespace of the dependency.

## Usage

### Java

The java sniffer can analyze the dependency reports generated
by [maven](https://maven.apache.org/plugins/maven-dependency-plugin/tree-mojo.html)
and [gradle](https://docs.gradle.org/current/userguide/viewing_debugging_dependencies.html) in order to do an exhaustive
search for dependencies.
You can call the script via the command line:

```shell
./run.sh --type [gradle|maven] [--artifact slf4j-api --package org.sl4jf] DEPENDENCY_REPORT
```

The options are the following:

* _--type_: either gradle or maven
* _--artifact_: artifactId of the coordinates of the dependency you are using, e.g. slf4j-api
* _--package_: package name of the dependency, e.g. org.sl4jf

It's always recommended to start searching by the artifactId and only if nothing comes up, switch to a more in depth
review with the package name.

#### Maven

Before running the sniffer ensure all dependencies of your project have already been downloaded and build the report:

```shell
./mvnw install
./mvnw org.apache.maven.plugins:maven-dependency-plugin:3.8.0:tree -DoutputType=json -DoutputFile=maven.json
```

Finally, you can call the script:

```shell
./run.sh --type maven --artifact slf4j-api maven.json
```

### Gradle

Before running the sniffer ensure all dependencies of your project have already been downloaded and build the report:

```shell
./gradlew build
./gradlew -q dependencies > gradle.txt
```

Finally, you can call the script:

```shell
./run.sh --type gradle --artifact slf4j-api gradle.txt
```
