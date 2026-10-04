#!/bin/bash
set -euo pipefail
exec > >(tee -a /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

export DEBIAN_FRONTEND=noninteractive

retry() {
  local attempt
  for attempt in {1..6}; do
    if "$@"; then
      return 0
    fi
    if [ "$attempt" -lt 6 ]; then
      echo "Command failed (attempt $attempt/6); retrying in 10 seconds: $*"
      sleep 10
    fi
  done
  echo "Command failed after 6 attempts: $*" >&2
  return 1
}

echo "Starting user_data setup for CPU LightGBM benchmark node"

retry apt-get -o Acquire::ForceIPv4=true -o Acquire::http::Timeout=15 -o APT::Update::Error-Mode=any update
retry apt-get -o Acquire::ForceIPv4=true -o Acquire::http::Timeout=15 install -y python3 python3-pip libgomp1

retry python3 -m pip install --upgrade pip
retry python3 -m pip install lightgbm scikit-learn pandas numpy kaggle

python3 -c "import lightgbm, sklearn, pandas, numpy; from importlib.metadata import version; print('ML imports OK; kaggle ' + version('kaggle'))"

mkdir -p /home/ubuntu/ml-benchmark
chown ubuntu:ubuntu /home/ubuntu/ml-benchmark

echo "CPU environment ready: lightgbm, scikit-learn, pandas, numpy, kaggle installed system-wide."
