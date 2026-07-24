#!/bin/bash
set -euo pipefail
docker port "$1" 5000 | head -n 1 | cut -d: -f2
