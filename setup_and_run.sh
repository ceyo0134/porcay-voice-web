#!/usr/bin/env bash
# Porçay RVC WebUI: kurulum + calistirma (Linux / Colab)
# Kullanim: bash setup_and_run.sh [gpu|cpu]
set -e
MODE="${1:-gpu}"
python -m pip install --upgrade pip setuptools wheel huggingface_hub
if [ "$MODE" = "gpu" ]; then
  python -m pip install torch==2.7.1+cu118 torchaudio==2.7.1+cu118 \
    --index-url https://download.pytorch.org/whl/cu118 --extra-index-url https://pypi.org/simple
  python -m pip install -r requirments_cu118_py312.txt
else
  python -m pip install -r requirments_cpu_py312.txt
fi
# Gerekli yardimci modeller (inference icin)
hf download lj1995/VoiceConversionWebUI --revision main --include "hubert_base/*" --local-dir assets
hf download lj1995/VoiceConversionWebUI rmvpe.pt --revision main --local-dir assets/rmvpe
# Web arayuzu (Colab'da --colab public gradio linki uretir)
python webui.py --colab --noautoopen
