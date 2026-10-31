"""Música original de Oceanica Terra — «smooth jazz» instrumental (piano eléctrico, bajo, batería suave y saxo sintetizado).

Uso: python3 jazz.py salida.wav [variante]
Variantes: 01 (la pista jazz-suave-01.m4a se conserva tal cual; regenerarla da una versión parecida, saxo, 90 BPM), 02 (piano nocturno, 78 BPM), 03 (saxo al atardecer, 96 BPM),
04 (brisa bossa con flauta, 100 BPM). 25 compases. Partes: intro (0-1), tema A (2-9), tema B con saxo (10-17), clímax (18-23), final (24).
Escribe salida.json con los segundos de cada parte ("final" = inicio del acorde final, para alinear con el cierre).
Composición propia: progresiones de jazz de dominio público (ii-V-I) y una melodía nueva; todo sintetizado,
sin muestras ni fragmentos de grabaciones de terceros. No imita ninguna canción concreta.
"""
import json, sys, wave
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

VAR = sys.argv[2] if len(sys.argv) > 2 else "01"
CONF = {
    "01": dict(bpm=90, tr=0, lead="sax", bat="suave", prog="A", frases=0, desde=10, estilo="smooth jazz con saxo"),
    "02": dict(bpm=78, tr=-5, lead="piano", bat="ligera", prog="B", frases=1, desde=6, estilo="piano eléctrico nocturno, muy tranquilo"),
    "03": dict(bpm=96, tr=2, lead="sax", bat="suave", prog="C", frases=2, desde=4, estilo="saxo al atardecer, más presente"),
    "04": dict(bpm=100, tr=4, lead="flauta", bat="bossa", prog="B", frases=3, desde=6, estilo="brisa bossa con flauta"),
}[VAR]
SR = 44100; BPM = CONF["bpm"]; BEAT = 60 / BPM; BAR = 4 * BEAT; NB = 25
N = int((NB * BAR + 6) * SR)
rng = np.random.default_rng(7 + int(VAR))
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


def flauta(m, dur, vel=1.0):
    """Flauta sintetizada: seno con algo de 2.º armónico, vibrato y soplo."""
    n = int((dur + 0.2) * SR); t = np.arange(n) / SR
    vib = 1 + 0.005 * np.sin(2 * np.pi * 5.0 * t) * np.clip((t - 0.2) / 0.3, 0, 1)
    ph = np.cumsum(mtof(m) * vib) / SR
    x = np.sin(2 * np.pi * ph) + 0.18 * np.sin(4 * np.pi * ph) + 0.06 * np.sin(6 * np.pi * ph)
    soplo = bp(rng.standard_normal(n), 2000, 7000) * 0.05 * (0.5 + 0.5 * np.exp(-t * 6))
    env = np.minimum(1, t / 0.05) * (1 - np.clip((t - dur) / 0.15, 0, 1))
    return (x + soplo) * env * vel


def lead(m, dur, vel):
    if CONF["lead"] == "piano":
        return epiano(m, dur, vel)
    if CONF["lead"] == "flauta":
        return flauta(m, dur, vel)
    return sax(m, dur, vel)


# Acordes (en Re bemol; la variante los transporta con CONF["tr"]), con 7.ª, 9.ª y 13.ª.
C = {
    "Ebm9": [51, 58, 61, 65, 66], "Ab13": [56, 60, 66, 65, 70], "Dbmaj9": [49, 56, 60, 63, 65],
    "Bbm9": [46, 53, 56, 60, 61], "Gbmaj7": [54, 58, 61, 65], "Fm7": [53, 56, 60, 63],
    "Ebm7": [51, 54, 58, 61], "Ab7sus": [56, 61, 63, 66], "Dbmaj7": [49, 53, 56, 60],
    "Gbmaj9": [54, 58, 61, 65, 68], "Fm9": [53, 56, 60, 63, 67], "Bbm7": [46, 53, 56, 61],
    "Eb9": [51, 55, 58, 61, 65], "C7alt": [48, 52, 58, 61, 63],
}
RAIZ = {"Ebm9": 39, "Ab13": 44, "Dbmaj9": 37, "Bbm9": 34, "Gbmaj7": 42, "Fm7": 41, "Ebm7": 39, "Ab7sus": 44,
        "Dbmaj7": 37, "Gbmaj9": 42, "Fm9": 41, "Bbm7": 34, "Eb9": 39, "C7alt": 36}
PROG = {
    # A: ii-V-I-vi y subdominante (la original)
    "A": (["Ebm9", "Ab13", "Dbmaj9", "Bbm9"], ["Gbmaj7", "Fm7", "Ebm7", "Ab7sus"]),
    # B: I-IV con color de 9.ª, muy estática y tranquila
    "B": (["Dbmaj9", "Gbmaj9", "Dbmaj9", "Gbmaj9"], ["Fm9", "Bbm7", "Ebm9", "Ab13"]),
    # C: vi-ii-V-I con dominante secundaria
    "C": (["Bbm9", "Eb9", "Ebm9", "Ab13"], ["Dbmaj9", "C7alt", "Fm9", "Ab7sus"]),
}
A, B = PROG[CONF["prog"]]
forma = [A[2], A[3]] + A * 2 + B * 2 + A + [B[0], B[3]] + ["Dbmaj9"]
assert len(forma) == NB, len(forma)
TR = CONF["tr"]

# Melodías nuevas (pentatónica de Re bemol con notas de paso), frases de 2 compases:
# (corchea de inicio, nota, duración en corcheas). Un juego distinto por variante.
JUEGOS = [
    [[(1, 73, 2), (3, 75, 1), (4, 77, 3), (8, 80, 2), (10, 77, 2), (12, 75, 4)],
     [(0, 73, 1), (1, 75, 1), (2, 77, 2), (5, 82, 3), (9, 80, 1), (10, 77, 1), (11, 75, 5)],
     [(2, 70, 2), (4, 73, 2), (6, 75, 1), (7, 77, 3), (11, 75, 1), (12, 73, 4)],
     [(1, 77, 1), (2, 80, 2), (4, 82, 4), (9, 80, 1), (10, 77, 2), (12, 80, 4)]],
    [[(0, 80, 3), (3, 77, 1), (4, 75, 4), (10, 73, 2), (12, 72, 4)],
     [(2, 73, 2), (4, 77, 2), (6, 80, 6), (13, 78, 3)],
     [(0, 77, 2), (2, 75, 2), (4, 73, 4), (9, 70, 1), (10, 73, 6)],
     [(1, 72, 1), (2, 73, 2), (4, 77, 3), (8, 75, 2), (10, 73, 6)]],
    [[(0, 68, 1), (1, 70, 1), (2, 73, 1), (3, 75, 3), (7, 73, 1), (8, 75, 2), (10, 77, 6)],
     [(1, 80, 2), (3, 77, 1), (4, 75, 2), (6, 73, 1), (7, 75, 5), (13, 70, 3)],
     [(0, 73, 2), (2, 77, 2), (4, 80, 2), (6, 82, 4), (11, 80, 1), (12, 77, 4)],
     [(2, 75, 1), (3, 77, 1), (4, 75, 2), (6, 73, 2), (8, 70, 2), (10, 73, 6)]],
    [[(0, 77, 1), (1, 80, 1), (2, 82, 2), (5, 80, 1), (6, 77, 2), (9, 75, 1), (10, 73, 6)],
     [(1, 73, 1), (2, 75, 1), (3, 77, 2), (6, 75, 1), (7, 73, 1), (8, 70, 4), (13, 72, 3)],
     [(0, 75, 2), (3, 77, 1), (4, 80, 3), (8, 82, 1), (9, 80, 1), (10, 77, 6)],
     [(2, 73, 1), (3, 75, 1), (4, 77, 1), (5, 75, 1), (6, 73, 2), (9, 72, 1), (10, 73, 6)]],
]
FRASES = JUEGOS[CONF["frases"]]
DESDE = CONF["desde"]
partes = {"intro": 0.0}
for b, ch in enumerate(forma):
    t0 = b * BAR
    if b == 2: partes["verso"] = t0
    if b == 10: partes["subida"] = t0
    if b == 18: partes["estribillo"] = t0
    if b == NB - 1: partes["final"] = t0
    final = b == NB - 1
    # Piano eléctrico: acorde en el 1 y anticipación sincopada (en la bossa, patrón partido)
    for k, m in enumerate(C[ch]):
        add(epiano(m + TR, BEAT * (4 if final else 1.4), 0.55), t0 + k * 0.012, 0.11, pan=-0.25)
        if not final:
            if CONF["bat"] == "bossa":
                for off in (1.5, 3.0):
                    add(epiano(m + TR, BEAT * 0.8, 0.4), t0 + off * BEAT + k * 0.008, 0.07, pan=-0.25)
            else:
                add(epiano(m + TR, BEAT * 1.6, 0.45), t0 + 1.5 * BEAT + k * 0.01, 0.09, pan=-0.25)
    # Bajo
    r = RAIZ[ch] + TR
    if final:
        add(bass(r, BAR * 1.5), t0, 0.5)
    elif b >= 2:
        if CONF["bat"] == "bossa":
            patron = [(0, r), (1.5, r + 7), (2, r + 7), (3.5, r)]
        elif CONF["bat"] == "ligera":
            patron = [(0, r), (2.5, r + 7)]
        else:
            patron = [(0, r), (1.5, r + 12 if b % 2 else r + 7), (2.5, r + 7), (3.5, r + 10 if b % 3 == 0 else r + 5)]
        for beat, mm in patron:
            add(bass(mm, BEAT * 0.9), t0 + beat * BEAT, 0.45)
    # Batería (desde el compás 2; más presente en el clímax)
    if 2 <= b < NB - 1:
        g = 1.25 if b >= 18 else 1.0
        if CONF["bat"] == "bossa":
            add(kick(), t0, 0.45 * g); add(kick(), t0 + 1.5 * BEAT, 0.3 * g)
            add(kick(), t0 + 2 * BEAT, 0.45 * g); add(kick(), t0 + 3.5 * BEAT, 0.3 * g)
            clave = [0, 1.5, 3] if b % 2 == 0 else [1, 2]
            for cb in clave:
                add(rim(), t0 + cb * BEAT, 0.16 * g)
            for e in range(8):
                add(hat(), t0 + e * BEAT / 2, (0.05 if e % 2 else 0.03) * g, pan=0.3)
        elif CONF["bat"] == "ligera":
            add(kick(), t0, 0.35 * g)
            add(rim(), t0 + 3 * BEAT, 0.1 * g)
            add(brush(BAR), t0, 0.009 * g, pan=-0.2)
            for e in range(4):
                add(hat(), t0 + e * BEAT, 0.035 * g, pan=0.3)
        else:
            add(kick(), t0, 0.5 * g); add(kick(), t0 + 2.5 * BEAT, 0.35 * g)
            add(rim(), t0 + BEAT, 0.18 * g); add(rim(), t0 + 3 * BEAT, 0.18 * g)
            for e in range(8):
                add(hat(open_=(e == 7)), t0 + e * BEAT / 2 + (0.03 if e % 2 else 0), 0.05 * g, pan=0.3)
            add(brush(BAR), t0, 0.012 * g, pan=-0.2)
    # Melodía principal (frases de 2 compases)
    if DESDE <= b < NB - 1 and (b - DESDE) % 2 == 0:
        fr = FRASES[((b - DESDE) // 2) % len(FRASES)]
        sube = 2 if b >= 18 and CONF["lead"] != "piano" else 0
        octava = 0 if CONF["lead"] == "flauta" else -12
        if CONF["lead"] == "piano":
            octava = 0
        g = {"sax": 0.12, "piano": 0.16, "flauta": 0.10}[CONF["lead"]]
        for c0, m, d in fr:
            add(lead(m + octava + sube + TR, d * BEAT / 2 * 0.95, 0.9 if b >= 18 else 0.75), t0 + c0 * BEAT / 2, g, pan=0.15)
    if final:
        nota = 61 + TR + (0 if CONF["lead"] != "flauta" else 12)
        add(lead(nota, BAR, 0.6), t0 + 0.3, {"sax": 0.08, "piano": 0.12, "flauta": 0.07}[CONF["lead"]], pan=0.15)

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
        "estilo": "smooth jazz instrumental (composición propia): " + CONF["estilo"], "variante": VAR}
json.dump(meta, open(salida.rsplit(".", 1)[0] + ".json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(meta, ensure_ascii=False))
