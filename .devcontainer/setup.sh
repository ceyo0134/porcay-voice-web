#!/usr/bin/env bash
set -e
sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg libsndfile1 libportaudio2 unzip
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirments_codespaces.txt
REL=https://github.com/ceyo0134/porcay-voice-web/releases/download/models-v1
mkdir -p assets/rmvpe
[ -f assets/rmvpe/rmvpe.pt ] || curl -L -o assets/rmvpe/rmvpe.pt $REL/rmvpe.pt
[ -d assets/hubert_base ] || { curl -L -o /tmp/hubert_base.zip $REL/hubert_base.zip && unzip -q -o /tmp/hubert_base.zip -d assets; }
