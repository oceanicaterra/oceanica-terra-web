"""Plantilla visual de Oceanica Terra para redes sociales.

Uso:  python3 plantilla.py especificacion.json carpeta_salida

La especificación (JSON) puede incluir:
  slug     : nombre corto en minúsculas y guiones (obligatorio)
  fuente   : texto del pie de las láminas, p. ej. "Fuente: OMI · SOLAS"
  slides   : [{"estilo": "dark"|"light", "html": "<div class='kicker'>…</div><h2>…</h2><p>…</p>"}]
             Clases disponibles: kicker, h1, h2, p, em, tag no|yes, table (th/td, tr.hl), cta.
             Usa {n} para el número total de láminas.
  facebook : {"kicker": "...", "titulo": "...", "texto": "..."}
  story    : {"fecha": "28 de octubre de 2026", "items": [{"titulo": "...", "fuente": "..."}]}

Genera: ig-<slug>-N.png (1080×1350), yt-<slug>-N.png (1080×1920) y yt-<slug>.mp4 (Short),
fb-<slug>.png (1200×630) y story-<slug>.png (1080×1920).
El Short lleva de fondo una música original de musica/ (rota según el slug; "musica": "<nombre>" en la
especificación fuerza una pista), con el clímax alineado al final del vídeo.
"""
import asyncio, html, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent


def ensure_fonts():
    """Letra de la marca desde el 31/10/2026: Inter (SIL OFL, gratuita)."""
    have = subprocess.run(["fc-list"], capture_output=True, text=True).stdout
    if "Inter" in have:
        return
    tmp = pathlib.Path("/tmp/gfonts")
    if not (tmp / "ofl/inter").exists():
        if not tmp.exists():
            subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                            "https://github.com/google/fonts", str(tmp)], check=True)
        subprocess.run(["git", "-C", str(tmp), "sparse-checkout", "add", "ofl/inter"], check=True)
    dest = pathlib.Path.home() / ".fonts"
    dest.mkdir(exist_ok=True)
    for f in (tmp / "ofl/inter").glob("*.ttf"):
        (dest / f.name).write_bytes(f.read_bytes())
    subprocess.run(["fc-cache", "-f"], check=True)


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
/* Identidad visual B «Apple + mar» (31/10/2026): fondos claros, letra Inter, azul océano y toques de naranja amanecer.
   El estilo «dark» de las especificaciones ya no es azul oscuro: es la variante «mar» (celeste suave). */
body{width:VARW;height:VARH;font-family:'Inter',-apple-system,'Segoe UI',Arial,sans-serif;color:#0B1D2E;overflow:hidden;letter-spacing:-.01em}
.s{position:relative;width:100%;height:100%;padding:VARPAD;display:flex;flex-direction:column;
   background:linear-gradient(180deg,#FFFFFF 0%,#F1F8FC 100%)}
.s.dark{background:linear-gradient(170deg,#F3FAFD 0%,#D5ECF7 100%);color:#0B1D2E}
.waves{position:absolute;left:0;width:100%;bottom:0;height:22%;opacity:.95}
.brand{font-weight:700;letter-spacing:.18em;font-size:VARBRAND;color:#0B1D2E}
.brand::before{content:"";display:inline-block;width:.62em;height:.62em;border-radius:50%;background:#0A72B5;margin-right:.55em;vertical-align:.02em}
.kicker{font-weight:600;font-size:VARK;color:#0A69A6;margin-top:VARGAP;letter-spacing:-.005em}
h1{font-weight:800;font-size:ZZTITLE;line-height:1.0;margin-top:.25em;letter-spacing:-.045em}
h2{font-weight:750;font-size:ZZSUB;line-height:1.06;margin-top:.3em;letter-spacing:-.03em}
p{font-size:VARP;line-height:1.4;margin-top:.7em;max-width:94%;color:#4A5D6E}
.dark p{color:#3E5568}
em{font-style:normal;background:linear-gradient(transparent 62%,rgba(10,114,181,.18) 0);color:#0B1D2E}
.dark em{background:linear-gradient(transparent 62%,rgba(226,98,42,.22) 0)}
.tag{display:inline-block;font-weight:700;font-size:VARK;padding:.3em .85em;border-radius:999px;margin-top:VARGAP}
.no{background:#E2622A;color:#fff}.yes{background:#1F6F4A;color:#fff}
table{width:100%;border-collapse:separate;border-spacing:0;margin-top:VARGAP;font-size:VART;position:relative;z-index:2;
   background:#fff;border-radius:22px;overflow:hidden;box-shadow:0 18px 40px -26px rgba(11,29,46,.35)}
th{font-weight:700;text-align:left;padding:.55em .55em;background:#E7F4FB;color:#0B1D2E}
td{padding:.55em .55em;border-top:2px solid #E1E7EC;vertical-align:top;background:#fff}
td:first-child{font-weight:600;color:#0A69A6}
tr.hl td{background:#FDEEE6;font-weight:600}
.foot{display:flex;justify-content:space-between;align-items:flex-end;position:relative;z-index:2;
   font-size:VARF;color:#5A6B7B;font-weight:500}
.dark .foot{color:#4A6378}
.num{font-weight:700}
.cta{display:inline-block;margin-top:VARGAP;background:#0A72B5;color:#fff;
   font-weight:700;font-size:VARK;padding:.6em 1.15em;border-radius:999px}
.content{position:relative;z-index:2;margin:auto 0;padding-bottom:8%}
.news{margin-top:VARGAP;background:#fff;border-radius:22px;padding:.7em .9em;box-shadow:0 14px 30px -22px rgba(11,29,46,.35)}
.news h3{font-weight:700;font-size:VARNEWS;line-height:1.14;color:#0B1D2E;letter-spacing:-.02em}
.news small{display:block;font-size:VARF;color:#0A69A6;margin-top:.4em;font-weight:600}
"""

WAVES = """<svg class="waves" viewBox="0 0 1000 200" preserveAspectRatio="none">
<path d="M0,90 C160,40 330,140 500,90 C670,40 840,140 1000,90 L1000,200 L0,200Z" fill="#C2E5F4" opacity=".6"/>
<path d="M0,130 C180,90 320,170 500,130 C680,90 820,170 1000,130 L1000,200 L0,200Z" fill="#8ACDE6" opacity=".45"/></svg>"""
WAVES_DARK = WAVES.replace("#C2E5F4", "#FFFFFF")


def page(w, h, scale, body, cls, foot_left="", foot_right=""):
    v = {"VARW": f"{w}px", "VARH": f"{h}px", "VARPAD": f"{int(86*scale)}px {int(80*scale)}px",
         "VARBRAND": f"{int(24*scale)}px", "VARK": f"{int(28*scale)}px", "VARGAP": f"{int(48*scale)}px",
         "ZZTITLE": f"{int(118*scale)}px", "ZZSUB": f"{int(66*scale)}px", "VARP": f"{int(38*scale)}px",
         "VART": f"{int(32*scale)}px", "VARF": f"{int(24*scale)}px", "VARNEWS": f"{int(44*scale)}px"}
    css = CSS
    for k, val in v.items():
        css = css.replace(k, val)
    waves = WAVES_DARK if cls == "dark" else WAVES
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{css}</style></head>'
            f'<body><div class="s {cls}"><div class="brand">OCEANICA TERRA</div><div class="content">{body}</div>'
            f'<div class="foot"><span>{foot_left}</span><span class="num">{foot_right}</span></div>{waves}</div></body></html>')


def words(htm):
    import re
    return len(re.sub(r"<[^>]+>", " ", htm).split())


async def render(spec, out):
    from playwright.async_api import async_playwright
    slug = spec["slug"]
    fuente = html.escape(spec.get("fuente", ""))
    slides = spec.get("slides", [])
    made = []
    async with async_playwright() as pw:
        b = await pw.chromium.launch()

        async def shot(htm, w, h, name):
            pg = await b.new_page(viewport={"width": w, "height": h})
            await pg.set_content(htm)
            await pg.evaluate("document.fonts.ready")
            await pg.screenshot(path=str(out / name))
            await pg.close()
            made.append(name)

        n = len(slides)
        for i, s in enumerate(slides, 1):
            cls = "dark" if s.get("estilo") == "dark" else ""
            body = s["html"].replace("{n}", str(n))
            await shot(page(1080, 1350, 1.0, body, cls, fuente, f"{i}/{n}"), 1080, 1350, f"ig-{slug}-{i}.png")
            ybody = body.replace("Enlace en la biografía", "Enlace en la descripción")
            await shot(page(1080, 1920, 1.3, ybody, cls, fuente, f"{i}/{n}"), 1080, 1920, f"yt-{slug}-{i}.png")
        if "facebook" in spec:
            f = spec["facebook"]
            body = (f'<div class="kicker">{html.escape(f.get("kicker", ""))}</div>'
                    f'<h1 style="font-size:84px">{html.escape(f["titulo"])}</h1>'
                    f'<p>{html.escape(f.get("texto", ""))}</p>')
            await shot(page(1200, 630, .78, body, "dark", "oceanicaterra.com"), 1200, 630, f"fb-{slug}.png")
        if "story" in spec:
            st = spec["story"]
            items = "".join(f'<div class="news"><h3>{html.escape(it["titulo"])}</h3>'
                            f'<small>Fuente: {html.escape(it["fuente"])}</small></div>' for it in st["items"][:3])
            body = (f'<div class="kicker">Lo que pasa hoy en el mar · {html.escape(st.get("fecha", ""))}</div>'
                    f'<h2>Noticias marítimas y portuarias</h2>{items}'
                    f'<span class="cta">Resúmenes completos en oceanicaterra.com</span>')
            await shot(page(1080, 1920, 1.25, body, "dark", "Resúmenes propios · cada noticia enlaza a su medio"),
                       1080, 1920, f"story-{slug}.png")
        await b.close()

    if slides:
        durs = [round(min(8.0, max(3.5, 2.5 + words(s["html"]) / 3.2)), 1) for s in slides]
        args = ["ffmpeg", "-y", "-loglevel", "error"]
        for i, d in enumerate(durs, 1):
            args += ["-loop", "1", "-t", str(d), "-i", str(out / f"yt-{slug}-{i}.png")]
        total = sum(durs) - 0.5 * (len(durs) - 1)
        # Música de fondo original (regla 5): el clímax del estribillo cae al final del vídeo.
        pistas = sorted(p for p in (ROOT / "musica").glob("*.m4a") if p.with_suffix(".json").exists())
        if spec.get("musica"):  # forzar una pista concreta, p. ej. "piano-suave-01"
            pistas = [p for p in pistas if p.stem == spec["musica"]] or pistas
        marca = [p for p in pistas if p.stem.startswith("jazz-suave-")]  # música de marca por defecto (musica/jazz.py)
        if marca and not spec.get("musica"):
            pistas = marca
        musica = pistas[sum(slug.encode()) % len(pistas)] if pistas else None
        if musica:
            meta = json.loads(musica.with_suffix(".json").read_text())
            print(f"Música: {musica.stem}")
            ini = max(0.0, meta["final"] + 1.5 - total)
            args += ["-ss", f"{ini:.2f}", "-t", f"{total:.2f}", "-i", str(musica)]
        else:
            args += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
        if len(durs) == 1:
            fc = "[0]format=yuv420p,fps=30[v]"
        else:
            parts, prev, off = [], "[0]", 0.0
            for i in range(1, len(durs)):
                off += durs[i - 1] - 0.5
                lab = "[v]" if i == len(durs) - 1 else f"[x{i}]"
                tail = ",format=yuv420p,fps=30" if i == len(durs) - 1 else ""
                parts.append(f"{prev}[{i}]xfade=transition=fade:duration=0.5:offset={off:.2f}{tail}{lab}")
                prev = lab
            fc = ";".join(parts)
        fc += (f";[{len(durs)}:a]afade=t=in:d=0.3,afade=t=out:st={max(0, total - 1):.2f}:d=1,"
               f"loudnorm=I=-14:TP=-1.5,aresample=48000[a]")
        args += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
                 "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-shortest", "-movflags", "+faststart",
                 str(out / f"yt-{slug}.mp4")]
        subprocess.run(args, check=True)
        made.append(f"yt-{slug}.mp4 ({total:.1f} s)")
        if total > 58:
            print("AVISO: el Short supera 58 s; reduce láminas o texto.")
    return made


if __name__ == "__main__":
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    ensure_fonts()
    for m in asyncio.run(render(spec, out)):
        print(m)
