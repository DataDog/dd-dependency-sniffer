# Datadog Dependency Sniffer

The Datadog Dependency Sniffer is a tool designed to scan and analyze the dependencies of a project, identifying the
actual location of specific dependencies in order to assist locating vulnerable dependencies discovered by Datadog's
[SCA](https://www.datadoghq.com/product/software-composition-analysis/).
It effectively handles scenarios where dependencies might be shaded or relocated, providing accurate insights into the
libraries your project relies on.

## Features

- **Comprehensive Scanning**: Thoroughly scans project dependencies to identify both direct and transitive usage.
- **Shading and Relocation Detection**: Accounts for shaded and relocated packages to provide more accurate results.
- **Customizable Search Criteria**: Specify the dependency you want to search for using patterns.
- **Cross-Platform Support**: Compatible with Windows, macOS, and Linux systems.
- **Language support**: Current version targets Java/JVM dependencies in Maven and Gradle projects

## Installation

1. **Clone the Repository**

```bash
git clone https://github.com/DataDog/dd-dependency-sniffer.git
cd dd-dependency-sniffer
```

## Usage

First ensure that you have the following software installed on your system:
1. [Docker](https://docs.docker.com/engine/install/)
2. [Bash](https://www.gnu.org/software/bash/)

The sniffer is capable of parsing and analyzing dependency tree reports from
both [Maven](https://maven.apache.org/plugins/maven-dependency-plugin/tree-mojo.html)
and [Gradle](https://docs.gradle.org/current/userguide/viewing_debugging_dependencies.html). It relies on the following
environment variables to provide access to your local dependencies:

- **_M2_HOME_** (by default `$HOME/.m2`) pointing to your local Maven repository.
- **_GRADLE_USER_HOME_** (by default `$HOME/.gradle`) pointing to your local Gradle repository.

You can download the provided script and run it:

```shell
curl "https://datadoghq.dev/dd-dependency-sniffer/run.sh" -o run.sh
chmod +x ./run.sh
./run.sh --type [gradle|maven] --artifact $ARTIFACT_ID --package $PACKAGE_NAME $REPORT
```

Or run it directly with:

```shell
curl -s "https://datadoghq.dev/dd-dependency-sniffer/run.sh" | bash -s -- --type [gradle|maven] --artifact $ARTIFACT_ID --package $PACKAGE_NAME $REPORT
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
run.sh --type maven --artifact slf4j-api maven.json
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
run.sh --type gradle --artifact slf4j-api gradle.txt
```

## Output
Once the script has been run, you will get an output similar to the following:

```text
The artifact with id 'slf4j-api' has been found in 2 dependencies:

1. 'nohttp-cli-0.0.11.jar' has matches in:
        - META-INF/maven/org.slf4j/slf4j-api/pom.properties

2. 'slf4j-api-2.0.16.jar' has matches in:
        - META-INF/MANIFEST.MF
        - META-INF/maven/org.slf4j/slf4j-api/pom.properties
```

In this case the project had a direct dependency with `slf4j-api:2.0.16`, but it was also shaded in `nohttp-cli:0.0.11`
