
# badcode

**badcode** mines code patterns that are unlikely to survive in a codebase. It exposes a gRPC service compatible with [lookout](https://github.com/src-d/lookout) to integrate it in the code review process.

## Rationale

**badcode** is built on the assumption that there are some anti-patterns that are often used but are unlikely to survive in a codebase, since they are often replaced with better versions. The goal of the project is then to build a model that can find such anti-patterns based on statistics of how many times a given pattern is added and deleted in a large amount of projects.

We cannot confirm yet to what extent this assumption is true. That is a goal of the project and is still a work in progress.

## How does it work?

**badcode** takes a list of git repositories, clones them, goes through every commit, parses all files and converts them into an abstract syntax tree, then keeps statistics about how many times each possible subtree is ever added or deleted in a commit. These statistics are then postprocessed to find common patterns that are unlikely to survive, that is what we call _bad code_.

Git cloning, history traversal and diff'ing relies on [pygit2](https://www.pygit2.org/).

We use [bblfsh](https://doc.bblf.sh/) to parse source code into a UAST (Universal Abstract Syntax Tree). That provides us with a language-independent approach, which works for any language that bblfsh has a driver for.

The main interface to apply the model is the [lookout](https://github.com/src-d/lookout) service, which can be used to post results from this analyzers as code reviews in GitHub.

## Status

This project is still in very early stage. Running over a few dozen (small) repositories is possible. The model is still quite immature and it will produce a lot of mispredictions. There are a few pieces hardcoded to analyze Go only.

## Getting Started

### With Docker

```bash
# Create a data directory
DATA_DIR="$(pwd)/data"
mkdir "$DATA_DIR"

# Create a file with GitHub repositories (`org/name`) to train with
echo "src-d/gitbase" > "$DATA_DIR/repos.txt"

# Train
docker run -v "$DATA_DIR":/code/data smolav/badcode train /code/data/data/repos.txt

# Inspect model
docker run -v "$DATA_DIR":/code/data smolav/badcode inspect

# Start analyzer
docker run -v "$DATA_DIR":/code/data smolav/badcode analyzer
```

### From Sources

libgit2 v0.27.0 is required. It can be installed inside a virtual environment. See `install.sh` for an example.

```
pipenv shell
pip install -e .
```

## Roadmap

- Support running on multiple language at the same time, producing one model per language.
- Use a better internal representation of trees to get smaller models and faster evaluation.
- Automate it end to end so that it can be deployed as a lookout analyzer without offline model training.
- Publish a Docker image.

## License

Copyright 2018 Santiago M. Mola

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
