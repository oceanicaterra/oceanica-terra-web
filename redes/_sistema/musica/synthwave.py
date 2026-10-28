"""Música original de Oceanica Terra — estilo dreamwave / chillwave 80's.

Uso: python3 synthwave.py salida.wav [--seed N]
Genera una pieza de ~65 s a 96 BPM (compás = 2.5 s):
  compases 0-3   intro   (pad + arpegio, filtro abriéndose)
  compases 4-11  verso   (bajo, batería suave)
  compases 12-15 subida  (redoble, ruido ascendente)
  compases 16-23 estribillo (melodía principal, momento de grandeza)
  compases 24-25 final   (acorde sostenido)
Escribe también salida.json con los segundos de cada parte.
Todo sintetizado: sin muestras ni material de terceros.
"""
import json, sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
NB = 26
N = int(NB * BAR * SR) + SR * 3
rng = np.random.default_rng(int(sys.argv[3]) if len(sys.argv) > 3 else 7)

L = np.zeros(N); R = np.zeros(N)
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def env(n, a, d, s, r, sus):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = np.clip((t - sus) / max(r, 1e-4), 0, 1)
    return e * (1 - rel) * (t < sus + r)
def saw(f, n, ph=0.0):
    t = np.arange(n) / SR
    return 2 * ((f * t + ph) % 1) - 1
def lp(x, fc, order=2):
    return sosfilt(butter(order, min(fc, SR / 2 - 100) / (SR / 2), 'low', output='sos'), x)
def hp(x, fc):
    return sosfilt(butter(2, fc / (SR / 2), 'high', output='sos'), x)
def add(buf, x, start, gain=1.0):
    i = int(start * SR); j = min(N, i + len(x))
    if j > i: buf[i:j] += x[: j - i] * gain

# Acordes (MIDI) — La menor / Do mayor
Am = [57, 60, 64]; F = [53, 57, 60]; C = [55, 60, 64]; G = [55, 59, 62]; Em = [52, 55, 59]
prog = ([Am, F, C, G] * 3) + [F, G, Am, G] + [F, G, Am, C, F, G, Am, C] + [F, C]
roots = {id(Am): 45, id(F): 41, id(C): 48, id(G): 43, id(Em): 40}

def section(b):
    return 'intro' if b < 4 else 'verso' if b < 12 else 'subida' if b < 16 else 'estribillo' if b < 24 else 'final'

pad_bus_L = np.zeros(N); pad_bus_R = np.zeros(N)
for b, ch in enumerate(prog):
    sec = section(b)
    n = int(BAR * SR * 1.15)
    cutoff = {'intro': 900 + 500 * b, 'verso': 2600, 'subida': 2600 + 700 * (b - 12), 'estribillo': 5200, 'final': 4000}[sec]
    notes = ch + [ch[0] + 12] if sec in ('estribillo', 'final') else ch
    for m in notes:
        for side, det in ((0, -0.09), (1, 0.09)):
            v = sum(saw(mtof(m + det + dd), n, rng.random()) for dd in (-0.05, 0, 0.05)) / 3
            v = lp(v, cutoff) * env(n, 0.35, 1.0, 0.85, 0.6, BAR * 1.05 if b < NB - 1 else BAR * 1.9)
            add(pad_bus_L if side == 0 else pad_bus_R, v, b * BAR, 0.075)

# Bajo con bombeo (sidechain) en corcheas
bass = np.zeros(N)
for b, ch in enumerate(prog):
    sec = section(b)
    if sec == 'intro': continue
    root = roots[id(ch)]
    for k in range(8):
        n = int(BEAT / 2 * SR)
        f = mtof(root)
        v = lp(0.6 * saw(f, n) + 0.4 * np.sin(2 * np.pi * f * np.arange(n) / SR), 700)
        add(bass, v * env(n, 0.005, 0.2, 0.6, 0.05, BEAT / 2 - 0.05), b * BAR + k * BEAT / 2, 0.30 if sec != 'final' or k == 0 else 0)

# Arpegio en semicorcheas con eco ping-pong
arpL = np.zeros(N); arpR = np.zeros(N)
for b, ch in enumerate(prog):
    if section(b) == 'final': continue
    pattern = [ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 24]
    for k in range(16):
        m = pattern[k % 4]
        n = int(BEAT / 4 * SR * 1.6)
        f = mtof(m)
        t = np.arange(n) / SR
        v = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + saw(f * 1.003, n) * 0.5
        v = lp(v, 3200) * env(n, 0.003, 0.12, 0.0, 0.05, 0.12)
        g = 0.05 if section(b) == 'intro' else 0.06
        add(arpL, v, b * BAR + k * BEAT / 4, g)
d = int(BEAT * 0.75 * SR)
eL = np.zeros(N); eR = np.zeros(N)
for r in range(1, 6):
    s = arpL * (0.45 ** r)
    tgt = eR if r % 2 else eL
    tgt[d * r:] += s[: N - d * r]
arpR = arpR + eR; arpL = arpL + eL

# Batería
drums = np.zeros(N); snare_bus = np.zeros(N)
def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
def snare():
    n = int(0.3 * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 1200) * np.exp(-t * 16) * 0.6 + np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25) * 0.5
def hat():
    n = int(0.06 * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7500) * np.exp(-t * 60)
K, S_, H = kick(), snare(), hat()
kick_times = []
for b in range(NB):
    sec = section(b)
    if sec in ('intro', 'final'): continue
    for beat in range(4):
        t0 = b * BAR + beat * BEAT
        if sec == 'estribillo' or beat in (0, 2) or sec == 'subida':
            add(drums, K, t0, 0.32); kick_times.append(t0)
        if beat in (1, 3) and sec != 'subida':
            add(snare_bus, S_, t0, 0.5)
        for h in range(2):
            add(drums, H, t0 + h * BEAT / 2, 0.07 if h else 0.04)
    if sec == 'subida':  # redoble creciente
        steps = 4 * (b - 11)
        for k in range(steps):
            add(snare_bus, S_, b * BAR + k * BAR / steps, 0.15 + 0.35 * ((b - 12) * BAR + k * BAR / steps) / (4 * BAR))
add(drums, K, 24 * BAR, 0.6)
add(snare_bus, S_, 24 * BAR, 0.6)

# Reverb larga (sala de los 80)
def ir(sec, seed):
    g = np.random.default_rng(seed); n = int(sec * SR); t = np.arange(n) / SR
    x = g.standard_normal(n) * np.exp(-t * 3.2 / sec)
    return x / np.sqrt((x ** 2).sum())
irL, irR = ir(2.6, 1), ir(2.6, 2)
sn_wetL = fftconvolve(snare_bus, irL)[:N] * 0.45; sn_wetR = fftconvolve(snare_bus, irR)[:N] * 0.45

# Ruido ascendente en la subida
n = int(4 * BAR * SR); t = np.arange(n) / SR
noise = rng.standard_normal(n) * (t / t[-1]) ** 2
riser = np.zeros(N);
seg = np.array_split(noise, 40); out = []
for i, s in enumerate(seg): out.append(sosfilt(butter(2, (300 + 9000 * i / 40) / (SR / 2), 'low', output='sos'), s))
add(riser, np.concatenate(out), 12 * BAR, 0.12)

# Melodía principal del estribillo (momento de grandeza)
mel = [  # (compás, tiempo, duración en tiempos, nota)
 (16,0,1.5,72),(16,1.5,.5,69),(16,2,1,72),(16,3,1,74),
 (17,0,1.5,74),(17,1.5,.5,71),(17,2,2,67),
 (18,0,1.5,76),(18,1.5,.5,74),(18,2,1,72),(18,3,1,69),
 (19,0,3,67),(19,3,1,64),
 (20,0,1.5,72),(20,1.5,.5,69),(20,2,1,72),(20,3,1,77),
 (21,0,1,76),(21,1,1,74),(21,2,1,71),(21,3,1,74),
 (22,0,2,72),(22,2,2,76),
 (23,0,4,79),(24,0,4,72),
]
leadL = np.zeros(N); leadR = np.zeros(N)
for bar, bt, dur, m in mel:
    n = int((dur * BEAT + 0.5) * SR); t = np.arange(n) / SR
    f = mtof(m) * (1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 0.4, 0, 1))
    ph = np.cumsum(f) / SR
    v = (2 * (ph % 1) - 1) * 0.5 + (2 * ((ph * 1.007) % 1) - 1) * 0.5 + 0.3 * np.sign(np.sin(2 * np.pi * ph * 0.5))
    v = lp(v, 3800) * env(n, 0.03, 0.4, 0.75, 0.35, dur * BEAT)
    add(leadL, v, bar * BAR + bt * BEAT, 0.19); add(leadR, v, bar * BAR + bt * BEAT + 0.012, 0.19)
ldL = fftconvolve(leadL, irL)[:N] * 0.7; ldR = fftconvolve(leadR, irR)[:N] * 0.7
dly = int(BEAT * 0.75 * SR)
leadL[dly:] += 0.3 * leadR[:-dly]; leadR[dly:] += 0.3 * leadL[:-dly]

# Bombeo (sidechain) para pad y bajo
duck = np.ones(N)
for t0 in kick_times:
    i = int(t0 * SR); n = int(BEAT * SR); tt = np.arange(n) / SR
    j = min(N, i + n); duck[i:j] = np.minimum(duck[i:j], (1 - 0.55 * np.exp(-tt * 9))[: j - i])
padL = (pad_bus_L + fftconvolve(pad_bus_L, irL)[:N] * 0.5) * duck
padR = (pad_bus_R + fftconvolve(pad_bus_R, irR)[:N] * 0.5) * duck

mixL = padL + bass * duck + arpL + drums + snare_bus * 0.35 + sn_wetL + riser + leadL + ldL
mixR = padR + bass * duck + arpR + drums + snare_bus * 0.35 + sn_wetR + riser + leadR + ldR
mix = np.stack([mixL, mixR], 1)
mix = hp(mix.T, 30).T
mix = np.tanh(mix * 1.2) / 1.2
mix = mix[: int((NB * BAR + 2.5) * SR)]
fade = int(2.0 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix /= np.max(np.abs(mix)) / 0.89

import wave
out = sys.argv[1]
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
json.dump({'bpm': BPM, 'compas_s': BAR, 'intro': 0, 'verso': 4 * BAR, 'subida': 12 * BAR,
           'estribillo': 16 * BAR, 'final': 24 * BAR, 'duracion': len(mix) / SR},
          open(out.rsplit('.', 1)[0] + '.json', 'w'), indent=1)
print(out, len(mix) / SR)
