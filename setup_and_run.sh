#!/usr/bin/env bash
# Porçay RVC WebUI: kurulum + calistirma (Linux / Colab)
# Kullanim: bash setup_and_run.sh [gpu|cpu]
set -e
MODE="${1:-gpu}"
python -m pip install --upgrade pip setuptools wheel
if [ "$MODE" = "gpu" ]; then
  python -m pip install torch==2.7.1+cu118 torchaudio==2.7.1+cu118 \
    --index-url https://download.pytorch.org/whl/cu118 --extra-index-url https://pypi.org/simple
  python -m pip install -r requirments_cu118_py312.txt
else
  python -m pip install -r requirments_cpu_py312.txt
fi
# Gerekli yardimci modeller (GitHub Release'ten, HuggingFace gerekmez)
REL=https://github.com/ceyo0134/porcay-voice-web/releases/download/models-v1
mkdir -p assets/rmvpe
[ -f assets/rmvpe/rmvpe.pt ] || curl -L -o assets/rmvpe/rmvpe.pt $REL/rmvpe.pt
[ -d assets/hubert_base ] || { curl -L -o /tmp/hubert_base.zip $REL/hubert_base.zip && unzip -q -o /tmp/hubert_base.zip -d assets; }
# Web arayuzu (Colab'da --colab public gradio linki uretir)
python webui.py --colab --noautoopen
