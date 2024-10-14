# Datadog Dependency Sniffer

The Datadog Dependency Sniffer is a powerful tool designed to efficiently scan and analyze the dependencies of a
project, identifying the usage of specific dependencies. It effectively handles scenarios where dependencies might be
shaded or relocated, providing accurate insights into the libraries your project relies on. This tool is particularly
useful for compliance with legal requirements, auditing security vulnerabilities, and managing software complexity.

## Features

- **Comprehensive Scanning**: Thoroughly scans project dependencies to identify both direct and transitive usage.
- **Shading and Relocation Detection**: Accounts for shaded and relocated packages to provide more accurate results.
- **Customizable Search Criteria**: Specify the dependency you want to search for using patterns.
- **Cross-Platform Support**: Compatible with Windows, macOS, and Linux systems.

## Installation

1. **Clone the Repository**

```bash
git clone https://github.com/DataDog/dd-dependency-sniffer.git
cd dd-dependency-sniffer
```

## Usage

The sniffer is capable of parsing and analyzing dependency tree reports from
both [Maven](https://maven.apache.org/plugins/maven-dependency-plugin/tree-mojo.html)
and [Gradle](https://docs.gradle.org/current/userguide/viewing_debugging_dependencies.html). It relies on the following
environment variables to provide access to your local dependencies:

- **_M2_HOME_** (by default `$HOME/.m2`) pointing to your local Maven repository.
- **_GRADLE_USER_HOME_** (by default `$HOME/.gradle`) pointing to your local Gradle repository.

You can run the script via the command line:

```shell
./run.sh --type [gradle|maven] --artifact $ARTIFACT_ID --package $PACKAGE_NAME $REPORT
```

The options are as follows:

- **_--type_**: Specify either `gradle` or `maven`.
- **Filtering options (pick one)**:
    - **_--artifact_**: Artifact ID of the Maven coordinates, e.g., `slf4j-api`.
    - **_--package_**: Package name prefix of the library, e.g., `org.slf4j`.
- **$REPORT**: Path of the dependency report provided by either Maven or Gradle.

It is recommended to start searching by the artifact ID and, if this approach is inconclusive, switch to package names
for greater accuracy.

### Maven

Ensure all dependencies are available in your local Maven repository and then execute the Maven dependency plugin
report, from your project run:

```shell
./mvnw install
./mvnw org.apache.maven.plugins:maven-dependency-plugin:3.8.0:tree -DoutputType=json -DoutputFile=maven.json
```

Run the script:

```shell
./run.sh --type maven --artifact slf4j-api maven.json
```

### Gradle

Ensure all dependencies are available in your local Gradle repository and then execute the Gradle dependencies task,
from your project run:

```shell
./gradlew build
./gradlew -q dependencies > gradle.txt
```

Run the script:

```shell
./run.sh --type gradle --artifact slf4j-api gradle.txt
```
