"""Música original de Oceanica Terra — piano eléctrico suave con cuerdas (estilo «calm autumn» de tendencia).

Uso: python3 piano.py salida.wav
~66 s a 72 BPM (compás = 3.333 s). Partes: intro (0-3), tema (4-11), clímax con cuerdas (12-17), final (18-19).
Escribe salida.json con los segundos de cada parte ("final" = inicio del acorde final, para alinear con el cierre).
Todo sintetizado: sin muestras ni material de terceros.
"""
import json, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100; BPM = 72; BEAT = 60 / BPM; BAR = 4 * BEAT; NB = 20
N = int((NB * BAR + 6) * SR)
rng = np.random.default_rng(11)
L = np.zeros(N); R = np.zeros(N)
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def lp(x, fc): return sosfilt(butter(2, min(fc, SR / 2 - 100) / (SR / 2), 'low', output='sos'), x)
def hp(x, fc): return sosfilt(butter(2, fc / (SR / 2), 'high', output='sos'), x)
def add(buf, x, t0, g):
    i = int(t0 * SR); j = min(N, i + len(x))
    if j > i: buf[i:j] += x[: j - i] * g

def epiano(m, dur, vel=1.0):
    """Piano eléctrico FM (tipo Rhodes): portadora + moduladora con índice que decae."""
    n = int((dur + 1.8) * SR); t = np.arange(n) / SR; f = mtof(m)
    idx = (1.6 * vel) * np.exp(-t * 3.0) + 0.15
    mod = np.sin(2 * np.pi * f * t) * idx
    car = np.sin(2 * np.pi * f * t + mod)
    tine = np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t * 18) * 0.25 * vel
    amp = np.exp(-t * (1.1 + m / 90)) * np.minimum(1, t / 0.004)
    rel = np.clip((t - dur) / 0.35, 0, 1)
    return (car + tine) * amp * (1 - rel) * vel

def strings(m, dur):
    n = int((dur + 1.2) * SR); t = np.arange(n) / SR
    v = np.zeros(n)
    for d in (-0.07, 0, 0.07):
        f = mtof(m + d) * (1 + 0.003 * np.sin(2 * np.pi * 5 * t + rng.random() * 6))
        ph = np.cumsum(f) / SR; v += 2 * (ph % 1) - 1
    v = lp(v / 3, 2200)
    a = np.clip(t / 0.9, 0, 1) * np.clip((dur + 1.0 - t) / 1.0, 0, 1)
    return v * a

# Progresión emotiva en Re mayor: I – V/7 – vi – IV  |  clímax: IV – V – vi – I
D = [50, 62, 66, 69, 74]; A = [45, 61, 64, 69, 73]; Bm = [47, 62, 66, 69, 74]; G = [43, 62, 67, 71, 74]
Em = [40, 62, 67, 71, 74]; Fsm = [42, 61, 66, 69, 73]
prog = [D, A, Bm, G] * 3 + [G, A, Bm, Fsm, G, A] + [D, D]

def sec(b): return 'intro' if b < 4 else 'tema' if b < 12 else 'climax' if b < 18 else 'final'

for b, ch in enumerate(prog):
    s = sec(b); t0 = b * BAR
    vel = {'intro': .55, 'tema': .7, 'climax': .85, 'final': .7}[s]
    # bajo (nota grave al inicio y a mitad de compás)
    add(L, epiano(ch[0], BAR * .9, vel), t0, .10); add(R, epiano(ch[0], BAR * .9, vel), t0, .10)
    # arpegio suave en corcheas
    if s != 'final':
        pat = [ch[1], ch[2], ch[3], ch[4], ch[3], ch[2], ch[3], ch[4]]
        for k, m in enumerate(pat):
            x = epiano(m, BEAT / 2, vel * (0.75 if k % 2 else 0.9))
            pan = 0.5 + 0.25 * np.sin(k)
            add(L, x, t0 + k * BEAT / 2 + rng.normal(0, .006), .07 * (1.2 - pan))
            add(R, x, t0 + k * BEAT / 2 + rng.normal(0, .006), .07 * (0.2 + pan))
    else:
        for k, m in enumerate(ch[1:]):  # acorde final rasgueado lento
            x = epiano(m, BAR * 1.8, .8); add(L, x, t0 + k * .09, .1); add(R, x, t0 + k * .09 + .01, .1)
    # cuerdas: entran suaves en el tema y crecen en el clímax
    if s in ('tema', 'climax', 'final'):
        g = {'tema': .018, 'climax': .045, 'final': .03}[s]
        for m in ch[1:4]:
            x = strings(m, BAR); add(L, x, t0, g); add(R, x, t0 + .013, g)
        if s == 'climax':
            x = strings(ch[0] + 12, BAR); add(L, x, t0, .03); add(R, x, t0, .03)

# Melodía del clímax (piano, octava alta) — momento de grandeza
mel = [(12,0,2,78),(12,2,1,76),(12,3,1,74),(13,0,2,76),(13,2,2,73),(14,0,1.5,74),(14,1.5,.5,76),(14,2,2,78),
       (15,0,3,73),(16,0,2,78),(16,2,1,79),(16,3,1,81),(17,0,4,81),(18,0,4,78)]
for bar, bt, dur, m in mel:
    x = epiano(m, dur * BEAT, .95); t0 = bar * BAR + bt * BEAT
    add(L, x, t0, .13); add(R, x, t0 + .008, .13)

def ir(s, seed):
    g = np.random.default_rng(seed); n = int(s * SR); t = np.arange(n) / SR
    x = g.standard_normal(n) * np.exp(-t * 3.5 / s); x = lp(x, 6000); return x / np.sqrt((x ** 2).sum())
wl = fftconvolve(L, ir(3.2, 1))[:N]; wr = fftconvolve(R, ir(3.2, 2))[:N]
mix = np.stack([L + .55 * wl, R + .55 * wr], 1)
mix = hp(mix.T, 35).T
mix = np.tanh(mix * 1.1) / 1.1
mix = mix[: int((NB * BAR + 2) * SR)]
fade = int(2.5 * SR); mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix /= np.max(np.abs(mix)) / .89
out = sys.argv[1]
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
json.dump({'estilo': 'piano suave con cuerdas', 'bpm': BPM, 'compas_s': BAR, 'tema': 4 * BAR, 'estribillo': 12 * BAR,
           'final': 18 * BAR, 'duracion': len(mix) / SR}, open(out.rsplit('.', 1)[0] + '.json', 'w'), indent=1)
print(out, len(mix) / SR)
