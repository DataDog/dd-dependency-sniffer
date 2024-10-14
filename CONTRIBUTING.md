# Contributing

## Contributions are welcomed

Pull requests for bug fixes are welcome, but before submitting new features or changes to current
functionality, please [open an issue](https://github.com/DataDog/dd-dependency-sniffer/issues/new)
and discuss your ideas or propose the changes you wish to make first. After a resolution is reached a [PR can be
submitted](#pull-request-guidelines) for review.

## Code contributions

### Development environment

Prior to contributing to the project, you can ensure your environment meets the following requirements:
* Valid [Docker](https://docs.docker.com/engine/install/) installation
* Shell script with [Bash](https://www.gnu.org/software/bash/) support
* Valid [Python 3.13+](https://docs.python.org/3/using/index.html) installation

### Automatic code formatting

This project includes a `.editorconfig` file for basic editor settings.
This file is supported by most common text editors.

## Pull Request Guidelines

### Draft first

When opening a pull request, please open it as a [draft](https://github.blog/2019-02-14-introducing-draft-pull-requests/) to not auto assign reviewers before you feel the pull request is in a reviewable state.

### Title Format

Pull request titles should briefly describe the proposed changes in a way that makes sense for the users.
They should be a sentence starting with an infinitive verb, and avoid using prefixes like `[PROD]` or `PROD - `.

>[!CAUTION]
> Don't title:
> * _New feature_: it doesn't describe the change
> * _npm package manager_: it doesn't start with an infinite verb

>[!TIP]
> Do instead: _Add support for npm in Node.js_

>[!NOTE]
> If the changes don't make sense for the users, add the `tag: no release note` label.

## Pull Request Reviews

### Review Expectations

After making you pull request ready for review by converting it from draft, you can expect getting an initial review comment within two working days, and a full review within a week of work.
If you don't receive any update, feel free to send a nice reminder to the assigned reviewers using pull request comments.

