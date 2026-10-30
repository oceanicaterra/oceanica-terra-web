"""Reel visual de Oceanica Terra (formato «poco texto, mucho movimiento»).

Uso:  python3 reel.py spec-reel.json carpeta_salida [--musica nombre] [--sin-musica]
      (si el spec trae "salida", ese es el nombre del archivo; p. ej. "story-quiz-<slug>.mp4")

Crea ig-<slug>-reel.mp4 (1080×1920, 30 fps) a partir de una lista de escenas animadas, todas
dibujadas con código (sin fotos ajenas). Regla de oro: una idea por pantalla y como mucho
6–8 palabras grandes; el detalle va en el carrusel.

Escenas disponibles (campo "tipo"):
  texto     {"lineas": ["UN SOLO BARCO", "BLOQUEÓ", "EL CANAL DE SUEZ"], "resaltar": 2, "dur": 2.4}
            Palabras grandes que aparecen una a una. "resaltar": índice de la línea en naranja.
  bloqueo   {"arriba": "Marzo de 2021", "abajo": "6 días atascado", "dur": 3.4}
            Vista cenital de un canal: un portacontenedores avanza, gira y queda atravesado.
  fila      {"numero": 400, "prefijo": "+", "etiqueta": "buques esperando", "dur": 3.2}
            El canal bloqueado con buques que se acumulan a ambos lados y un contador.
  contador  {"numero": 9600, "antes": "US$", "despues": "millones", "etiqueta": "...", "nota": "...", "dur": 3.2}
            Cifra que sube de 0 al valor, con etiqueta y nota pequeña.
  tamanos   {"barcos": [["Handysize", 0.42, "20–35 mil TPM"], ...], "titulo": "...", "dur": 4.5}
            Siluetas laterales de buques que van creciendo una tras otra (escala relativa 0–1).
  quiz      {"pregunta": "¿...?", "opciones": ["A", "B", "C"], "correcta": 0, "explicacion": "...", "cuenta": 5, "dur": 10}
            Pregunta con opciones, cuenta regresiva y la respuesta correcta resaltada (historias interactivas).
  cta       {"pregunta": "¿...?", "linea": "Síguenos · @oceanicaterra", "dur": 3.0}
"""
import json, math, pathlib, subprocess, sys

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = pathlib.Path(__file__).resolve().parent
W, H, FPS = 1080, 1920, 30
NAVY, NAVY2 = (11, 37, 69), (11, 58, 87)
NARANJA, CIELO, BLANCO = (217, 72, 15), (111, 192, 222), (255, 255, 255)
ARENA, ARENA2, AGUA, AGUA2 = (214, 190, 140), (196, 168, 116), (24, 92, 130), (20, 78, 112)
COLORES_CONT = [(217, 72, 15), (11, 110, 143), (230, 180, 60), (90, 140, 70), (180, 60, 60), (240, 240, 240)]


def fuente(peso, tam):
    for p in [pathlib.Path.home() / ".fonts" / f"IBMPlexSansCondensed-{peso}.ttf",
              pathlib.Path(f"/tmp/gfonts/ofl/ibmplexsanscondensed/IBMPlexSansCondensed-{peso}.ttf")]:
        if p.exists():
            return ImageFont.truetype(str(p), tam)
    return ImageFont.load_default()


def ease_out(t):
    t = min(max(t, 0), 1)
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = min(max(t, 0), 1)
    c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2


def fondo():
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    for y in range(0, H, 8):
        k = y / H
        c = tuple(int(NAVY2[i] * (1 - k) + NAVY[i] * k) for i in range(3))
        d.rectangle([0, y, W, y + 8], fill=c)
    return im


FONDO = None


def base():
    global FONDO
    if FONDO is None:
        FONDO = fondo()
    im = FONDO.copy()
    d = ImageDraw.Draw(im)
    d.text((70, 90), "OCEANICA TERRA", font=fuente("Bold", 34), fill=CIELO)
    return im, d


def texto_centrado(d, y, txt, f, color, x=None, sombra=False):
    bb = d.textbbox((0, 0), txt, font=f)
    w = bb[2] - bb[0]
    xx = (W - w) // 2 - bb[0] if x is None else x
    if sombra:
        d.text((xx + 4, y + 4), txt, font=f, fill=(0, 0, 0))
    d.text((xx, y), txt, font=f, fill=color)
    return bb[3] - bb[1]


def ajustar(d, txt, peso, tam, ancho):
    while tam > 40:
        f = fuente(peso, tam)
        bb = d.textbbox((0, 0), txt, font=f)
        if bb[2] - bb[0] <= ancho:
            return f
        tam -= 4
    return fuente(peso, tam)


def envolver(d, txt, peso, tam, ancho):
    f = fuente(peso, tam)
    lineas, actual = [], ""
    for p in txt.split():
        prueba = (actual + " " + p).strip()
        if d.textbbox((0, 0), prueba, font=f)[2] <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    lineas.append(actual)
    return lineas, f


# ---------- escenas ----------

def esc_texto(e, t, dur):
    im, d = base()
    lineas = e["lineas"]
    n = len(lineas)
    tams = [ajustar(d, l, "Bold", 190, W - 140) for l in lineas]
    alturas = [d.textbbox((0, 0), l, font=f)[3] for l, f in zip(lineas, tams)]
    total = sum(alturas) + 30 * (n - 1)
    y = (H - total) // 2
    paso = min(0.45, (dur * 0.6) / max(n, 1))
    for i, (l, f, h) in enumerate(zip(lineas, tams, alturas)):
        k = ease_back((t - i * paso) / 0.35)
        if k <= 0:
            y += h + 30
            continue
        col = NARANJA if e.get("resaltar") == i else BLANCO
        capa = Image.new("RGBA", (W, h + 60), (0, 0, 0, 0))
        dc = ImageDraw.Draw(capa)
        texto_centrado(dc, 10, l, f, col + (255,))
        s = 0.6 + 0.4 * k
        cw, ch = int(W * s), int((h + 60) * s)
        capa = capa.resize((max(cw, 1), max(ch, 1)))
        alpha = capa.split()[3].point(lambda a: int(a * min(1, k)))
        capa.putalpha(alpha)
        im.paste(capa, ((W - cw) // 2, y + (h + 60 - ch) // 2), capa)
        y += h + 30
    return im


def dibujar_canal(im, x0=330, x1=750):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 360, W, 1560], fill=ARENA)
    for k in range(0, W, 60):
        d.line([(k, 360), (k + 120, 1560)], fill=ARENA2, width=3)
    d.rectangle([x0, 360, x1, 1560], fill=AGUA)
    for y in range(380, 1560, 70):
        d.line([(x0 + 40, y), (x0 + 110, y)], fill=AGUA2, width=4)
        d.line([(x1 - 140, y + 35), (x1 - 70, y + 35)], fill=AGUA2, width=4)
    return d


def buque_cenital(largo=640, ancho=96):
    """Portacontenedores visto desde arriba, proa hacia arriba (imagen RGBA)."""
    im = Image.new("RGBA", (ancho + 20, largo + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 10, 10, ancho + 10, largo + 10
    d.polygon([(x0, y0 + 90), ((x0 + x1) // 2, y0), (x1, y0 + 90), (x1, y1 - 20), (x0, y1 - 20)], fill=(40, 40, 50))
    d.rounded_rectangle([x0, y1 - 60, x1, y1], radius=16, fill=(40, 40, 50))
    y = y0 + 100
    i = 0
    while y < y1 - 130:
        for j in range(3):
            cx = x0 + 8 + j * ((ancho - 16) // 3)
            d.rectangle([cx, y, cx + (ancho - 16) // 3 - 4, y + 34], fill=COLORES_CONT[(i + j * 2) % len(COLORES_CONT)])
        y += 40
        i += 1
    d.rectangle([x0 + 10, y1 - 110, x1 - 10, y1 - 70], fill=(240, 240, 240))
    return im


BUQUE = None


def esc_bloqueo(e, t, dur):
    global BUQUE
    if BUQUE is None:
        BUQUE = buque_cenital()
    im, d = base()
    dibujar_canal(im)
    k1 = ease_out(t / (dur * 0.35))
    k2 = ease_out((t - dur * 0.35) / (dur * 0.35))
    cy = 1500 - k1 * 540
    ang = -62 * k2
    b = BUQUE.rotate(ang, expand=True, resample=Image.BICUBIC)
    im.paste(b, (540 - b.width // 2, int(cy - b.height // 2)), b)
    d = ImageDraw.Draw(im)
    if k2 > 0.95:
        pulso = 0.5 + 0.5 * math.sin((t - dur * 0.7) * 10)
        r = 70 + 14 * pulso
        d.ellipse([540 - r, 960 - r - 330, 540 + r, 960 + r - 330], outline=NARANJA, width=12)
        d.line([(540 - r * 0.6, 630 - r * 0.6), (540 + r * 0.6, 630 + r * 0.6)], fill=NARANJA, width=12)
    f1, f2 = fuente("Bold", 80), fuente("Bold", 96)
    texto_centrado(d, 200, e.get("arriba", ""), f1, CIELO)
    if t > dur * 0.55:
        texto_centrado(d, 1620, e.get("abajo", ""), f2, BLANCO, sombra=True)
    return im


def buque_icono(escala=1.0):
    return buque_cenital(int(220 * escala), int(44 * escala))


ICONO = None


def esc_fila(e, t, dur):
    global BUQUE, ICONO
    if BUQUE is None:
        BUQUE = buque_cenital()
    if ICONO is None:
        ICONO = buque_icono(0.8)
    im, d = base()
    dibujar_canal(im)
    b = BUQUE.rotate(-62, expand=True, resample=Image.BICUBIC)
    im.paste(b, (540 - b.width // 2, 960 - b.height // 2), b)
    abajo = ICONO
    arriba = ICONO.rotate(180)
    puestos = [(400, 1250, abajo), (560, 1250, abajo), (400, 380, arriba), (560, 380, arriba),
               (400, 1440, abajo), (560, 1440, abajo), (400, 200, arriba), (560, 200, arriba)]
    n = int(len(puestos) * ease_out(t / (dur * 0.7)) + 0.5)
    for x, y, ic in puestos[:n]:
        im.paste(ic, (x, y), ic)
    d = ImageDraw.Draw(im)
    val = int(e["numero"] * ease_out(t / (dur * 0.75)))
    txt = f"{e.get('prefijo', '')}{val:,}".replace(",", ".")
    d.rounded_rectangle([110, 1560, W - 110, 1860], radius=30, fill=NAVY)
    texto_centrado(d, 1570, txt, fuente("Bold", 170), NARANJA)
    et = e.get("etiqueta", "")
    texto_centrado(d, 1770, et, ajustar(d, et, "Bold", 70, W - 300), BLANCO)
    return im


def esc_contador(e, t, dur):
    im, d = base()
    val = e["numero"] * ease_out(t / (dur * 0.7))
    txt = f"{int(val):,}".replace(",", ".")
    texto_centrado(d, 620, e.get("antes", ""), fuente("Bold", 90), CIELO)
    texto_centrado(d, 730, txt, ajustar(d, txt, "Bold", 300, W - 140), NARANJA)
    texto_centrado(d, 1060, e.get("despues", ""), fuente("Bold", 110), BLANCO)
    if t > dur * 0.35:
        lineas, f = envolver(d, e.get("etiqueta", ""), "Medium", 64, W - 200)
        y = 1220
        for l in lineas:
            texto_centrado(d, y, l, f, BLANCO)
            y += 80
    if e.get("nota"):
        texto_centrado(d, 1700, e["nota"], fuente("Medium", 40), CIELO)
    return im


def silueta_lateral(largo, alto, color=(230, 236, 242)):
    im = Image.new("RGBA", (largo + 10, alto * 3 + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y_cub = alto * 2
    d.polygon([(0, y_cub), (largo, y_cub), (largo - alto * 0.5, y_cub + alto), (alto * 0.2, y_cub + alto)], fill=color)
    n = max(2, int(largo / (alto * 1.4)))
    paso = (largo * 0.78) / n
    for i in range(n):
        x = largo * 0.06 + i * paso
        d.rectangle([x, y_cub - alto * 0.18, x + paso * 0.7, y_cub], fill=(120, 140, 160))
    d.rectangle([largo * 0.86, y_cub - alto * 1.2, largo * 0.97, y_cub], fill=color)
    return im


def esc_tamanos(e, t, dur):
    im, d = base()
    texto_centrado(d, 230, e.get("titulo", ""), ajustar(d, e.get("titulo", ""), "Bold", 96, W - 140), BLANCO)
    barcos = e["barcos"]
    n = len(barcos)
    paso = (dur * 0.8) / n
    y = 520
    for i, (nombre, escala, sub) in enumerate(barcos):
        k = ease_out((t - i * paso) / 0.5)
        if k <= 0:
            break
        largo = int(880 * escala * k) + 1
        alto = max(12, int(70 * escala))
        s = silueta_lateral(largo, alto, NARANJA if i == n - 1 else (230, 236, 242))
        im.paste(s, (100, y + 150 - s.height), s)
        d.text((100, y + 165), nombre, font=fuente("Bold", 64), fill=NARANJA if i == n - 1 else BLANCO)
        d.text((100 + d.textbbox((0, 0), nombre + "  ", font=fuente("Bold", 64))[2], y + 180), sub,
               font=fuente("Medium", 44), fill=CIELO)
        y += 300
    return im


def esc_cta(e, t, dur):
    im, d = base()
    k = ease_back(t / 0.4)
    lineas, f = envolver(d, e["pregunta"], "Bold", 110, W - 160)
    y = 650
    for l in lineas:
        texto_centrado(d, y + int((1 - k) * 60), l, f, BLANCO)
        y += 125
    if t > 0.6:
        fb = fuente("Bold", 54)
        txt = e.get("linea", "Síguenos · @oceanicaterra")
        bb = d.textbbox((0, 0), txt, font=fb)
        w = bb[2] - bb[0] + 80
        d.rounded_rectangle([(W - w) // 2, y + 80, (W + w) // 2, y + 200], radius=18, fill=NARANJA)
        texto_centrado(d, y + 108, txt, fb, BLANCO)
    return im


def esc_quiz(e, t, dur):
    """Pregunta con 3 opciones, cuenta regresiva y revelación de la respuesta correcta."""
    im, d = base()
    texto_centrado(d, 230, e.get("kicker", "PREGUNTA DEL DÍA"), fuente("Bold", 56), NARANJA)
    lineas, f = envolver(d, e["pregunta"], "Bold", 92, W - 160)
    y = 330
    for l in lineas:
        texto_centrado(d, y, l, f, BLANCO)
        y += 104
    t_cuenta = e.get("cuenta", 5)
    t_rev = 1.2 + t_cuenta
    y = max(y + 60, 760)
    letras = "ABCD"
    for i, op in enumerate(e["opciones"]):
        k = ease_out((t - 0.3 - i * 0.25) / 0.4)
        if k <= 0:
            continue
        correcta = i == e["correcta"]
        revelado = t >= t_rev
        if revelado and correcta:
            fondo_c, borde, col = NARANJA, NARANJA, BLANCO
        elif revelado:
            fondo_c, borde, col = (20, 45, 75), (60, 80, 105), (120, 140, 160)
        else:
            fondo_c, borde, col = (16, 52, 88), CIELO, BLANCO
        x0 = 110 + int((1 - k) * 80)
        d.rounded_rectangle([x0, y, W - 110, y + 150], radius=28, fill=fondo_c, outline=borde, width=5)
        d.text((x0 + 40, y + 38), letras[i], font=fuente("Bold", 70), fill=col)
        fo = ajustar(d, op, "Bold", 64, W - 360)
        d.text((x0 + 130, y + 42), op, font=fo, fill=col)
        if revelado and correcta:
            d.line([(W - 220, y + 78), (W - 190, y + 108), (W - 140, y + 46)], fill=BLANCO, width=14, joint="curve")
        y += 185
    if 1.2 <= t < t_rev:
        n = int(t_rev - t) + 1
        cx, cy, r = W // 2, y + 140, 90
        frac = (t_rev - t) - int(t_rev - t)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(60, 80, 105), width=14)
        d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * frac, fill=NARANJA, width=14)
        texto_centrado(d, cy - 70, str(n), fuente("Bold", 120), BLANCO)
        texto_centrado(d, cy + 120, "Piensa tu respuesta...", fuente("Medium", 50), CIELO)
    elif t >= t_rev and e.get("explicacion"):
        k = ease_out((t - t_rev - 0.3) / 0.5)
        if k > 0:
            lineas, f = envolver(d, e["explicacion"], "Medium", 58, W - 200)
            yy = y + 60
            for l in lineas:
                texto_centrado(d, yy, l, f, BLANCO)
                yy += 74
    return im


ESCENAS = {"quiz": esc_quiz, "texto": esc_texto, "bloqueo": esc_bloqueo, "fila": esc_fila, "contador": esc_contador,
           "tamanos": esc_tamanos, "cta": esc_cta}


def elegir_musica(slug, nombre=None):
    pistas = sorted(p.stem for p in (ROOT / "musica").glob("*.m4a") if (ROOT / "musica" / f"{p.stem}.json").exists())
    if not pistas:
        return None, None
    if nombre not in pistas:
        nombre = pistas[sum(map(ord, slug)) % len(pistas)]
    return ROOT / "musica" / f"{nombre}.m4a", json.loads((ROOT / "musica" / f"{nombre}.json").read_text())


def main():
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text())
    out_dir = pathlib.Path(sys.argv[2])
    args = sys.argv[3:]
    slug = spec["slug"]
    total = sum(e["dur"] for e in spec["escenas"])
    salida = out_dir / spec.get("salida", f"ig-{slug}-reel.mp4")
    m4a, meta = (None, None) if "--sin-musica" in args else \
        elegir_musica(slug, args[args.index("--musica") + 1] if "--musica" in args else None)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-"]
    if m4a:
        ini = max(0.0, meta["final"] + 1.5 - total)
        cmd += ["-ss", f"{ini:.2f}", "-t", f"{total:.2f}", "-i", str(m4a), "-filter_complex",
                f"[1:a]afade=t=in:d=0.3,afade=t=out:st={max(0, total - 1):.2f}:d=1,loudnorm=I=-14:TP=-1.5,aresample=48000[a]",
                "-map", "0:v", "-map", "[a]"]
    else:
        cmd += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-shortest", "-movflags", "+faststart", str(salida)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for e in spec["escenas"]:
        fn = ESCENAS[e["tipo"]]
        nfr = round(e["dur"] * FPS)
        for i in range(nfr):
            p.stdin.write(fn(e, i / FPS, e["dur"]).convert("RGB").tobytes())
    p.stdin.close()
    p.wait()
    print(f"{salida.name} ({total:.1f} s; {len(spec['escenas'])} escenas; música: {m4a.stem if m4a else 'ninguna'})")


if __name__ == "__main__":
    main()
