# README

Autodocstr is a tool to automatically generate documentation for your python project.
Autodocstr leverages [LibCST](https://github.com/instagram/libcst) and [Large Language Models](https://openai.com/blog/openai-codex) to generate documentation for your python project.

## Install

To install autodocstr, simply:

```bash
pip install autodocstr
```

Sign up for an [OpenAI API key](https://beta.openai.com/docs/api-reference/authentication) and set it as an environment variable:

```bash
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Then from the root of your python project run:

```bash
# warning: make sure you have a backup of your project before running this command
autodocstr
```

## Features

Autodoc will generate a docstring for every function that has no docstring.
Functions that have a docstring will be ignored.

## Development

To contribute to autodocstr, you can clone the repository and install the dependencies:

```bash
conda create -n autodocstr python=3.8 poetry -y
conda activate autodocstr
poetry install
poetry run pytest
```

## Release

To create a release, you can use the following commands:

```bash
poetry config http-basic.pypi username password
# test release
poetry config repositories.test-pypi https://test.pypi.org/legacy/
poetry config pypi-token.test-pypi pypy-tkoe-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
poetry config pypi-token.pypi pypy-token-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
poetry version prerelease
poetry publish -r test-pypi --build
poetry publish --build
```
