#!/bin/bash

# Extract version from pyproject.toml
grep -m 1 'version = "[^"]*"' pyproject.toml | cut -d '"' -f 2
