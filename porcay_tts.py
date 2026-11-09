"""Yazi -> Porcay sesi (RVC) + otomatik GitHub 'outputs' klasorune MP3 yukleme.

Calistirma:  python porcay_tts.py          (http://localhost:7870)
Ortam degiskenleri (opsiyonel, otomatik yukleme icin):
  GH_REPO   = sahip/repo            (ornek: ceyo0134/PojavLauncher)
  GH_TOKEN  = o repoya yazma yetkisi olan token
  PORCAY_BRANCH = outputs dalinin adi (varsayilan: porcay-outputs)
"""
import os, sys, time, json, base64, asyncio, threading, traceback, urllib.request

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("weight_root", "assets/weights")
os.environ.setdefault("weight_pymss_root", "assets/pymss_weights")
os.environ.setdefault("index_root", "logs")
os.environ.setdefault("outside_index_root", "assets/indices")
os.environ.setdefault("rmvpe_root", "assets/rmvpe")
os.environ.setdefault("RVC_CUDA_GRAPH", "0")
sys.path.insert(0, os.getcwd())

import numpy as np
import soundfile as sf
import gradio as gr
import edge_tts
from configs.config import Config
from infer.vc.modules import VC

MODEL = os.environ.get("PORCAY_MODEL", "PorcayV2_e300_s3600.pth")
BRANCH = os.environ.get("PORCAY_BRANCH", "porcay-outputs")
OUT_DIR = "outputs"
WATCH_DIRS = ["outputs", "opt"]  # toplu cevirme sekmesinin varsayilan cikti klasoru: opt
AUDIO_EXT = (".wav", ".mp3", ".flac", ".ogg", ".m4a")
os.makedirs(OUT_DIR, exist_ok=True)

config = Config()
vc = VC(config)
vc.get_vc(MODEL)
pushed = set()
lock = threading.Lock()


def save_mp3(path_noext, audio, sr):
    """MP3 yazar (MP3 40 kHz desteklemez, 44.1 kHz'e cevirir); olmazsa WAV'a duser."""
    from math import gcd
    from scipy.signal import resample_poly
    try:
        a = audio.astype(np.float32)
        if a.dtype != np.float32 or np.abs(a).max() > 1.5:
            a = a / 32768.0
        if sr not in (8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000):
            g = gcd(44100, int(sr))
            a = resample_poly(a, 44100 // g, int(sr) // g).astype(np.float32)
            sr = 44100
        p = path_noext + ".mp3"
        sf.write(p, np.clip(a, -1, 1), int(sr), format="MP3")
        return p
    except Exception:
        p = path_noext + ".wav"
        sf.write(p, audio, sr)
        return p


def push(path):
    """Dosyayi GitHub'daki outputs/ klasorune yukler. (link, mesaj) dondurur."""
    repo, token = os.environ.get("GH_REPO"), os.environ.get("GH_TOKEN")
    name = os.path.basename(path)
    if not (repo and token):
        return None, "GitHub'a yuklenmedi (GH_REPO/GH_TOKEN yok), dosya yerelde: " + path
    try:
        data = base64.b64encode(open(path, "rb").read()).decode()
        body = json.dumps({"message": "Porcay output " + name, "branch": BRANCH, "content": data}).encode()
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/contents/outputs/{name}",
            data=body, method="PUT",
            headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json"})
        urllib.request.urlopen(req, timeout=120).read()
        link = f"https://github.com/{repo}/raw/{BRANCH}/outputs/{name}"
        return link, "GitHub'a yuklendi: " + link
    except Exception as e:
        return None, f"GitHub yukleme hatasi: {e}"


def convert(wav_path, transpose=0):
    status, res = vc.vc_single(0, wav_path, int(transpose), "rmvpe", "", 0.0, 0, 0.25, 0.33)
    sr, audio = res if res else (None, None)
    if sr is None:
        raise RuntimeError(status)
    return sr, audio


VOICES = {"Ahmet (erkek)": "tr-TR-AhmetNeural", "Emel (kadin)": "tr-TR-EmelNeural"}


def text_to_porcay(text, voice, transpose):
    text = (text or "").strip()
    if not text:
        return None, "Bir metin yaz."
    stamp = time.strftime("%Y%m%d-%H%M%S")
    tts_wav = os.path.join("TEMP", f"tts-{stamp}.mp3")
    os.makedirs("TEMP", exist_ok=True)
    try:
        asyncio.run(edge_tts.Communicate(text, VOICES[voice]).save(tts_wav))
        sr, audio = convert(tts_wav, transpose)
        out = save_mp3(os.path.join(OUT_DIR, f"porcay-{stamp}"), audio, sr)
        with lock:
            pushed.add(os.path.abspath(out))
        link, msg = push(out)
        return out, msg
    except Exception:
        return None, "Hata:\n" + traceback.format_exc()[-800:]


def watcher():
    """outputs/ ve opt/ klasorlerine dusen yeni ses dosyalarini MP3 yapip GitHub'a yukler."""
    seen_size = {}
    while True:
        time.sleep(6)
        for d in WATCH_DIRS:
            if not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                p = os.path.abspath(os.path.join(d, f))
                if not f.lower().endswith(AUDIO_EXT):
                    continue
                with lock:
                    if p in pushed:
                        continue
                try:
                    size = os.path.getsize(p)
                    if seen_size.get(p) != size:  # dosya hala yaziliyor olabilir
                        seen_size[p] = size
                        continue
                    if not f.lower().endswith(".mp3"):
                        a, sr = sf.read(p)
                        mp3 = save_mp3(os.path.join(OUT_DIR, os.path.splitext(f)[0]), a, sr)
                        with lock:
                            pushed.add(os.path.abspath(mp3))
                    else:
                        mp3 = p
                    with lock:
                        pushed.add(p)
                    print(push(mp3)[1], flush=True)
                except Exception as e:
                    print("watcher hata:", e, flush=True)


with gr.Blocks(title="Porcay Ses Klonu - Yazidan Ses") as demo:
    gr.Markdown("## Yazi -> Porcay sesi\nMetni yaz, Turkce sese cevrilir, sonra Porcay modeliyle donusturulur. "
                "Sonuc MP3 olarak GitHub'daki `outputs` klasorune de yuklenir.")
    txt = gr.Textbox(label="Metin", lines=4, placeholder="Merhaba, bu bir deneme.")
    with gr.Row():
        voice = gr.Dropdown(list(VOICES), value="Ahmet (erkek)", label="Temel ses")
        tr = gr.Number(value=0, label="Ton kaydirma (yari ses). Erkek->erkek 0")
    btn = gr.Button("Porcay sesiyle olustur", variant="primary")
    audio_out = gr.Audio(label="Sonuc", type="filepath")
    info = gr.Textbox(label="Durum")
    btn.click(text_to_porcay, [txt, voice, tr], [audio_out, info])

if __name__ == "__main__":
    threading.Thread(target=watcher, daemon=True).start()
    demo.queue().launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORCAY_PORT", "7870")), inbrowser=False)
