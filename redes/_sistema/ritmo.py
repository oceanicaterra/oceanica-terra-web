"""Versión rítmica de un Short para Instagram Reels (Oceanica Terra).

Uso:  python3 ritmo.py carpeta slug [--musica nombre] [--sin-musica]

Lee las láminas yt-<slug>-N.png (1080×1920) que genera plantilla.py y crea ig-<slug>-ritmo.mp4:
  - cortes secos (sin fundidos): portada 2,2 s, cierre 3,0 s, láminas interiores 3,0–4,6 s según
    la cantidad de texto que tienen;
  - zoom lento (3,5 %) sobre cada lámina para que siempre haya movimiento;
  - en la última lámina cambia el botón «Enlace en la descripción» por «Enlace en la biografía»;
  - música original de musica/ (la misma rotación que la plantilla) como respaldo, con el clímax al
    final. La tarea «Música de Reels» añade después en Buffer una pista de la biblioteca de Instagram
    y baja a 0 el volumen del vídeo. Si esa tarea no llega a ejecutarse, el Reel sale con esta música.
Duración típica: 20–26 s.
"""
import json, pathlib, subprocess, sys, tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent
NARANJA = np.array([217, 72, 15])
FUENTES = [pathlib.Path.home() / ".fonts" / "IBMPlexSansCondensed-Bold.ttf",
           pathlib.Path("/tmp/gfonts/ofl/ibmplexsanscondensed/IBMPlexSansCondensed-Bold.ttf")]


def densidad(png):
    """Fracción de píxeles de texto (aprox.) en la zona central de la lámina."""
    a = np.asarray(Image.open(png).convert("L").resize((270, 480))).astype(int)
    zona = a[60:420]
    fondo = np.median(zona)
    return float((abs(zona - fondo) > 60).mean())


def duraciones(pngs):
    n = len(pngs)
    out = []
    for i, p in enumerate(pngs):
        if i == 0:
            out.append(2.2)
        elif i == n - 1:
            out.append(3.0)
        else:
            d = densidad(p)  # ~0.02 poco texto · ~0.12 tabla densa
            out.append(round(min(4.6, max(3.0, 3.0 + (d - 0.03) * 18)), 1))
    return out


def cambiar_cta(src, dst, texto="Enlace en la biografía · oceanicaterra.com"):
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(int)
    m = (np.abs(a - NARANJA) < 14).all(axis=2)
    filas = np.where(m.sum(1) > 200)[0]
    fuente = next((f for f in FUENTES if f.exists()), None)
    if len(filas) < 40 or fuente is None:
        im.save(dst)
        return False
    y0, y1 = int(filas.min()), int(filas.max())
    cols = np.where(m[y0:y1 + 1].sum(0) > 5)[0]
    x0, x1 = int(cols.min()), int(cols.max())
    btn = a[y0:y1 + 1, x0:x1 + 1]
    blancos = btn.min(2) > 200
    ys, xs = np.where(blancos)
    alto_txt, padx = int(ys.max() - ys.min()), int(xs.min())
    arriba, abajo = a[y0 - 6].copy(), a[y1 + 6].copy()
    for k, y in enumerate(range(y0 - 3, y1 + 4)):
        t = k / (y1 - y0 + 6)
        a[y] = (arriba * (1 - t) + abajo * t).astype(int)
    im = Image.fromarray(a.astype("uint8"))
    d = ImageDraw.Draw(im)
    tam = 10
    while True:
        f2 = ImageFont.truetype(str(fuente), tam + 1)
        bb = f2.getbbox(texto)
        if bb[3] - bb[1] > alto_txt:
            break
        tam += 1
    f = ImageFont.truetype(str(fuente), tam)
    bb = f.getbbox(texto)
    d.rounded_rectangle([x0, y0, x0 + padx * 2 + bb[2] - bb[0], y1], radius=8, fill=tuple(NARANJA))
    d.text((x0 + padx - bb[0], y0 + ((y1 - y0) - (bb[3] - bb[1])) // 2 - bb[1]), texto, font=f, fill=(255, 255, 255))
    im.save(dst)
    return True


MUSICA_MARCA = "jazz-suave-01"  # pista de respaldo de la marca (musica/jazz.py)


def elegir_musica(slug, nombre=None):
    pistas = sorted(p.stem for p in (ROOT / "musica").glob("*.m4a") if (ROOT / "musica" / f"{p.stem}.json").exists())
    if not pistas:
        return None, None
    if nombre not in pistas:  # música de marca por defecto (smooth jazz original); si falta, rotación por slug
        nombre = MUSICA_MARCA if MUSICA_MARCA in pistas else pistas[sum(map(ord, slug)) % len(pistas)]
    return ROOT / "musica" / f"{nombre}.m4a", json.loads((ROOT / "musica" / f"{nombre}.json").read_text())


def main():
    carpeta, slug = pathlib.Path(sys.argv[1]), sys.argv[2]
    args = sys.argv[3:]
    nombre = args[args.index("--musica") + 1] if "--musica" in args else None
    pngs = sorted(carpeta.glob(f"yt-{slug}-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
    if not pngs:
        sys.exit(f"No hay láminas yt-{slug}-N.png en {carpeta}")
    durs = duraciones(pngs)
    total = round(sum(durs), 2)
    with tempfile.TemporaryDirectory() as tmp:
        ultima = pathlib.Path(tmp) / "ultima.png"
        cambiada = cambiar_cta(pngs[-1], ultima)
        fuentes = pngs[:-1] + [ultima]
        cmd, fc = ["ffmpeg", "-y", "-loglevel", "error"], ""
        for i, (p, d) in enumerate(zip(fuentes, durs)):
            fr = round(d * 30)
            cmd += ["-i", str(p)]
            fc += (f"[{i}:v]scale=2160:3840,zoompan=z='1+0.035*on/{fr}':x='iw/2-(iw/zoom/2)':"
                   f"y='ih/2-(ih/zoom/2)':d={fr}:s=1080x1920:fps=30,setsar=1,trim=end_frame={fr}[v{i}];")
        fc += "".join(f"[v{i}]" for i in range(len(fuentes))) + f"concat=n={len(fuentes)}:v=1:a=0,format=yuv420p[v]"
        m4a, meta = (None, None) if "--sin-musica" in args else elegir_musica(slug, nombre)
        if m4a:
            ini = max(0.0, meta["final"] + 1.5 - total)
            cmd += ["-ss", f"{ini:.2f}", "-t", f"{total:.2f}", "-i", str(m4a)]
            fc += (f";[{len(fuentes)}:a]afade=t=in:d=0.3,afade=t=out:st={max(0, total - 1):.2f}:d=1,"
                   "loudnorm=I=-14:TP=-1.5,aresample=48000[a]")
        else:
            cmd += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=48000:cl=stereo"]
            fc += f";[{len(fuentes)}:a]anull[a]"
        salida = carpeta / f"ig-{slug}-ritmo.mp4"
        cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "19", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(salida)]
        subprocess.run(cmd, check=True)
    print(f"{salida.name} ({total:.1f} s; láminas {durs}; CTA biografía: {'sí' if cambiada else 'no'}; "
          f"música: {m4a.stem if m4a else 'ninguna'})")


if __name__ == "__main__":
    main()
