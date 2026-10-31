"""Música original de Oceanica Terra — «smooth jazz» instrumental (piano eléctrico, bajo, batería suave y saxo sintetizado).

Uso: python3 jazz.py salida.wav [semilla]
~66 s a 90 BPM (compás = 2,667 s). Partes: intro (0-1), tema A (2-9), tema B con saxo (10-17), clímax (18-23), final (24).
Escribe salida.json con los segundos de cada parte ("final" = inicio del acorde final, para alinear con el cierre).
Composición propia: progresiones de jazz de dominio público (ii-V-I) y una melodía nueva; todo sintetizado,
sin muestras ni fragmentos de grabaciones de terceros. No imita ninguna canción concreta.
"""
import json, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100; BPM = 90; BEAT = 60 / BPM; BAR = 4 * BEAT; NB = 25
N = int((NB * BAR + 6) * SR)
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 7
rng = np.random.default_rng(SEED)
L = np.zeros(N); R = np.zeros(N)


def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def lp(x, fc): return sosfilt(butter(2, min(fc, SR / 2 - 100) / (SR / 2), 'low', output='sos'), x)
def hp(x, fc): return sosfilt(butter(2, fc / (SR / 2), 'high', output='sos'), x)
def bp(x, lo, hi): return sosfilt(butter(2, [lo / (SR / 2), hi / (SR / 2)], 'band', output='sos'), x)


def add(x, t0, g=1.0, pan=0.0):
    i = int(t0 * SR); j = min(N, i + len(x))
    if j > i:
        L[i:j] += x[: j - i] * g * (1 - pan) ; R[i:j] += x[: j - i] * g * (1 + pan)


def epiano(m, dur, vel=1.0):
    n = int((dur + 1.5) * SR); t = np.arange(n) / SR; f = mtof(m)
    idx = (1.4 * vel) * np.exp(-t * 3.5) + 0.12
    car = np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * f * t) * idx)
    tine = np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t * 20) * 0.2 * vel
    amp = np.exp(-t * (1.0 + m / 100)) * np.minimum(1, t / 0.004)
    rel = np.clip((t - dur) / 0.3, 0, 1)
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)
    return (car + tine) * amp * (1 - rel) * vel * trem


def bass(m, dur):
    n = int((dur + 0.3) * SR); t = np.arange(n) / SR; f = mtof(m)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sign(np.sin(2 * np.pi * f * t))
    amp = np.exp(-t * 1.6) * np.minimum(1, t / 0.006) * (1 - np.clip((t - dur) / 0.08, 0, 1))
    return lp(x * amp, 900)


def sax(m, dur, vel=1.0):
    """Saxo sintetizado: diente de sierra filtrado, vibrato tardío, aliento y ataque suave."""
    n = int((dur + 0.25) * SR); t = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.2 * t) * np.clip((t - 0.25) / 0.4, 0, 1)
    f = mtof(m) * vib * (1 - 0.01 * np.exp(-t * 25))
    ph = np.cumsum(f) / SR
    saw = 2 * (ph % 1) - 1
    x = lp(saw, 1800 + 1400 * vel)
    breath = bp(rng.standard_normal(n), 1500, 5000) * 0.06
    env = np.minimum(1, t / 0.06) * (1 - np.clip((t - dur) / 0.2, 0, 1)) * (0.85 + 0.15 * np.exp(-t * 2))
    return (x + breath) * env * vel


def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 55 + 70 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def rim():
    n = int(0.12 * SR); t = np.arange(n) / SR
    return (bp(rng.standard_normal(n), 1500, 4500) * 0.6 + np.sin(2 * np.pi * 1700 * t) * 0.4) * np.exp(-t * 45)


def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-t * (14 if open_ else 70))


def brush(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    return bp(rng.standard_normal(n), 2500, 9000) * (0.4 + 0.6 * np.abs(np.sin(np.pi * t / BEAT)))


# Progresión (tonalidad de Re bemol, típica del género): ii-V-I-vi y variaciones; acordes con 7.ª y 9.ª.
C = {
    "Ebm9": [51, 58, 61, 65, 66], "Ab13": [56, 60, 66, 65, 70], "Dbmaj9": [49, 56, 60, 63, 65],
    "Bbm9": [46, 53, 56, 60, 61], "Gbmaj7": [54, 58, 61, 65], "Fm7": [53, 56, 60, 63],
    "Ebm7": [51, 54, 58, 61], "Ab7sus": [56, 61, 63, 66], "Dbmaj7": [49, 53, 56, 60],
}
RAIZ = {"Ebm9": 39, "Ab13": 44, "Dbmaj9": 37, "Bbm9": 34, "Gbmaj7": 42, "Fm7": 41, "Ebm7": 39, "Ab7sus": 44, "Dbmaj7": 37}
A = ["Ebm9", "Ab13", "Dbmaj9", "Bbm9"]
B = ["Gbmaj7", "Fm7", "Ebm7", "Ab7sus"]
forma = (["Dbmaj9", "Gbmaj7"] + A * 2 + B * 2 + A + ["Gbmaj7", "Ab13"] + ["Dbmaj9"])
assert len(forma) == NB, len(forma)

# Melodía nueva (escala pentatónica de Db con notas de paso), frases de 2 compases: (corchea de inicio, nota, duración en corcheas)
FRASES = [
    [(1, 73, 2), (3, 75, 1), (4, 77, 3), (8, 80, 2), (10, 77, 2), (12, 75, 4)],
    [(0, 73, 1), (1, 75, 1), (2, 77, 2), (5, 82, 3), (9, 80, 1), (10, 77, 1), (11, 75, 5)],
    [(2, 70, 2), (4, 73, 2), (6, 75, 1), (7, 77, 3), (11, 75, 1), (12, 73, 4)],
    [(1, 77, 1), (2, 80, 2), (4, 82, 4), (9, 80, 1), (10, 77, 2), (12, 80, 4)],
]

t = 0.0
partes = {"intro": 0.0}
for b, ch in enumerate(forma):
    t0 = b * BAR
    if b == 2: partes["verso"] = t0
    if b == 10: partes["subida"] = t0
    if b == 18: partes["estribillo"] = t0
    if b == NB - 1: partes["final"] = t0
    final = b == NB - 1
    # Piano eléctrico: acorde en el 1 y anticipación sincopada en el «y» del 2
    for k, m in enumerate(C[ch]):
        add(epiano(m, BEAT * (4 if final else 1.4), 0.55), t0 + k * 0.012, 0.11, pan=-0.25)
        if not final:
            add(epiano(m, BEAT * 1.6, 0.45), t0 + 1.5 * BEAT + k * 0.01, 0.09, pan=-0.25)
    # Bajo
    r = RAIZ[ch]
    if final:
        add(bass(r, BAR * 1.5), t0, 0.5)
    elif b >= 2:
        for beat, mm in [(0, r), (1.5, r + 12 if b % 2 else r + 7), (2.5, r + 7), (3.5, r + 10 if b % 3 == 0 else r + 5)]:
            add(bass(mm, BEAT * 0.9), t0 + beat * BEAT, 0.45)
    # Batería suave (desde el compás 2; más presente en el clímax)
    if 2 <= b < NB - 1:
        g = 1.25 if b >= 18 else 1.0
        add(kick(), t0, 0.5 * g); add(kick(), t0 + 2.5 * BEAT, 0.35 * g)
        add(rim(), t0 + BEAT, 0.18 * g); add(rim(), t0 + 3 * BEAT, 0.18 * g)
        for e in range(8):
            add(hat(open_=(e == 7)), t0 + e * BEAT / 2 + (0.03 if e % 2 else 0), 0.05 * g, pan=0.3)
        add(brush(BAR), t0, 0.012 * g, pan=-0.2)
    # Saxo: tema B y clímax (frases de 2 compases)
    if 10 <= b < NB - 1 and b % 2 == 0:
        fr = FRASES[(b // 2) % len(FRASES)]
        sube = 2 if b >= 18 else 0
        for c0, m, d in fr:
            add(sax(m - 12 + sube, d * BEAT / 2 * 0.95, 0.9 if b >= 18 else 0.75), t0 + c0 * BEAT / 2, 0.12, pan=0.15)
    # Nota final del saxo
    if final:
        add(sax(61 - 12 + 12, BAR, 0.6), t0 + 0.3, 0.08, pan=0.15)

# Reverberación ligera
n_ir = int(1.6 * SR); ti = np.arange(n_ir) / SR
ir = rng.standard_normal(n_ir) * np.exp(-ti * 3.2)
ir = lp(ir, 5000); ir /= np.sqrt(np.sum(ir ** 2))
Lw = fftconvolve(L, ir)[:N]; Rw = fftconvolve(R, np.roll(ir, 211))[:N]
L = L * 0.82 + Lw * 0.22; R = R * 0.82 + Rw * 0.22
fin = int((NB * BAR + 4) * SR)
L, R = L[:fin], R[:fin]
fade = np.ones(fin); k = int(3 * SR); fade[-k:] = np.linspace(1, 0, k)
L *= fade; R *= fade
peak = max(np.abs(L).max(), np.abs(R).max()) or 1
st = (np.stack([L, R], 1) / peak * 0.89 * 32767).astype(np.int16)
salida = sys.argv[1]
with wave.open(salida, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
meta = {"bpm": BPM, "compas_s": round(BAR, 3), **{k: round(v, 2) for k, v in partes.items()}, "duracion": round(fin / SR, 2),
        "estilo": "smooth jazz instrumental (composición propia)"}
json.dump(meta, open(salida.rsplit(".", 1)[0] + ".json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(meta, ensure_ascii=False))
