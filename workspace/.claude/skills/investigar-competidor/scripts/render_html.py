#!/usr/bin/env python3
"""render_html.py — convierte entregas/informe.json en informe.html (tablero) e informe.md.

Uso:  python3 render_html.py entregas/informe.json
Solo usa la biblioteca estándar. Valida el JSON y sale con código 1 y un mensaje claro si falta algo.
"""

import html
import json
import sys
from collections import Counter
from pathlib import Path

REQUERIDOS = ("tema", "fecha", "resumen_ejecutivo", "hallazgos")
COLOR_IMPACTO = {"alto": "#c0392b", "medio": "#d68910", "bajo": "#5d6d7e"}


def e(x) -> str:
    return html.escape(str(x))


def validar(inf: dict) -> list[str]:
    errores = [f"falta «{c}»" for c in REQUERIDOS if not inf.get(c)]
    for i, h in enumerate(inf.get("hallazgos") or [], 1):
        for c in ("titulo", "detalle", "impacto", "fuentes"):
            if not h.get(c):
                errores.append(f"hallazgo {i}: falta «{c}»")
    return errores


def tarjeta(h: dict) -> str:
    color = COLOR_IMPACTO.get(h.get("impacto"), "#5d6d7e")
    conf = float(h.get("confianza") or 0)
    fuentes = "".join(
        f'<li><a href="{e(f.get("url"))}" target="_blank">{e(f.get("titulo") or f.get("url"))}</a>'
        f'<blockquote>“{e(f.get("cita", ""))}”</blockquote></li>'
        for f in h.get("fuentes", [])
    )
    nuevo = '<span class="tag nuevo">NUEVO</span>' if h.get("novedad") else ""
    return f"""
    <article class="card" style="border-left-color:{color}">
      <div class="meta"><span class="tag" style="background:{color}">{e(h.get('impacto','')).upper()}</span>
        <span class="tag gris">{e(h.get('categoria',''))}</span>{nuevo}
        <span class="conf" title="confianza"><span style="width:{conf*100:.0f}%"></span></span>
        <small>{conf:.0%}</small></div>
      <h3>{e(h['titulo'])}</h3><p>{e(h['detalle'])}</p>
      <details><summary>Fuentes verificadas ({len(h.get('fuentes', []))})</summary><ul>{fuentes}</ul></details>
    </article>"""


def lista(titulo: str, items: list, clase: str) -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{e(i)}</li>" for i in items)
    return f'<section class="caja {clase}"><h2>{titulo}</h2><ul>{lis}</ul></section>'


def a_html(inf: dict) -> str:
    hs = sorted(inf["hallazgos"], key=lambda h: ({"alto": 0, "medio": 1, "bajo": 2}.get(h.get("impacto"), 3),
                                                  -float(h.get("confianza") or 0)))
    imp = Counter(h.get("impacto") for h in hs)
    n_fuentes = len({f.get("url") for h in hs for f in h.get("fuentes", [])})
    nuevos = sum(1 for h in hs if h.get("novedad"))
    kpis = [("Hallazgos", len(hs)), ("Impacto alto", imp.get("alto", 0)),
            ("Novedades", nuevos), ("Fuentes verificadas", n_fuentes)]
    kpi_html = "".join(f'<div class="kpi"><b>{v}</b><span>{k}</span></div>' for k, v in kpis)
    descartadas = "".join(f"<li>{e(d.get('url'))} — {e(d.get('motivo'))}</li>"
                          for d in inf.get("fuentes_descartadas") or [])
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inteligencia competitiva · {e(inf['tema'])}</title>
<style>
:root{{--bg:#f6f7f9;--fg:#1c2833;--card:#fff;--mut:#5d6d7e}}
@media (prefers-color-scheme:dark){{:root{{--bg:#11161c;--fg:#e5e8eb;--card:#1b222b;--mut:#9aa5b1}}}}
body{{font-family:system-ui,sans-serif;background:var(--bg);color:var(--fg);margin:0;padding:2rem;max-width:1100px;margin:auto}}
header h1{{margin:.2rem 0}} header small{{color:var(--mut)}}
.resumen{{background:var(--card);padding:1.2rem 1.5rem;border-radius:12px;font-size:1.08rem;line-height:1.5}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1.2rem 0}}
.kpi{{background:var(--card);border-radius:12px;padding:1rem;text-align:center}}
.kpi b{{display:block;font-size:2rem}} .kpi span{{color:var(--mut);font-size:.85rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1rem}}
.card{{background:var(--card);border-radius:12px;padding:1rem 1.2rem;border-left:6px solid}}
.card h3{{margin:.5rem 0 .3rem}} .card p{{line-height:1.45}}
.meta{{display:flex;gap:.4rem;align-items:center;flex-wrap:wrap}}
.tag{{color:#fff;font-size:.7rem;padding:.15rem .5rem;border-radius:99px;font-weight:600}}
.tag.gris{{background:#7f8c8d}} .tag.nuevo{{background:#1e8449}}
.conf{{flex:0 0 70px;height:6px;background:#d5d8dc;border-radius:3px;overflow:hidden;margin-left:auto}}
.conf span{{display:block;height:100%;background:#2874a6}}
blockquote{{margin:.3rem 0 .6rem;padding-left:.7rem;border-left:3px solid #aab7b8;color:var(--mut);font-size:.9rem}}
.cols{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem;margin-top:1.5rem}}
.caja{{background:var(--card);border-radius:12px;padding:.5rem 1.2rem}}
.amenazas h2{{color:#c0392b}} .oportunidades h2{{color:#1e8449}} .preguntas h2{{color:#2874a6}}
footer{{margin-top:2rem;color:var(--mut);font-size:.8rem}} a{{color:#2874a6}}
</style></head><body>
<header><small>INFORME DE INTELIGENCIA COMPETITIVA · {e(inf['fecha'])}</small><h1>{e(inf['tema'])}</h1></header>
<p class="resumen">{e(inf['resumen_ejecutivo'])}</p>
<div class="kpis">{kpi_html}</div>
<div class="grid">{''.join(tarjeta(h) for h in hs)}</div>
<div class="cols">{lista('Amenazas', inf.get('amenazas'), 'amenazas')}
{lista('Oportunidades', inf.get('oportunidades'), 'oportunidades')}
{lista('Preguntas abiertas', inf.get('preguntas_abiertas'), 'preguntas')}</div>
{f'<details class="caja"><summary>Fuentes descartadas ({len(inf.get("fuentes_descartadas") or [])})</summary><ul>{descartadas}</ul></details>' if descartadas else ''}
<footer>Cada cita fue comprobada por código contra la página original (mcp__vigia__verificar_cita)
y el informe no se entregó hasta pasar el hook de verificación.</footer>
</body></html>"""


def a_md(inf: dict) -> str:
    out = [f"# {inf['tema']} — inteligencia competitiva ({inf['fecha']})", "", inf["resumen_ejecutivo"], ""]
    for h in inf["hallazgos"]:
        nuevo = " 🆕" if h.get("novedad") else ""
        out += [f"## [{h.get('impacto', '').upper()}] {h['titulo']}{nuevo}",
                f"*{h.get('categoria', '')} · confianza {float(h.get('confianza') or 0):.0%}*", "", h["detalle"], ""]
        out += [f"> “{f.get('cita')}” — [{f.get('titulo') or f.get('url')}]({f.get('url')})" for f in h["fuentes"]]
        out.append("")
    for titulo, clave in (("Amenazas", "amenazas"), ("Oportunidades", "oportunidades"),
                          ("Preguntas abiertas", "preguntas_abiertas")):
        if inf.get(clave):
            out += [f"## {titulo}", *[f"- {x}" for x in inf[clave]], ""]
    return "\n".join(out)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("uso: render_html.py entregas/informe.json")
    ruta = Path(sys.argv[1])
    try:
        inf = json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as err:
        sys.exit(f"ERROR leyendo {ruta}: {err}")
    if errores := validar(inf):
        sys.exit("ERROR, corrige el JSON:\n- " + "\n- ".join(errores))
    ruta.with_suffix(".html").write_text(a_html(inf), encoding="utf-8")
    ruta.with_suffix(".md").write_text(a_md(inf), encoding="utf-8")
    print(f"OK: {ruta.with_suffix('.html')} y {ruta.with_suffix('.md')} "
          f"({len(inf['hallazgos'])} hallazgos)")


if __name__ == "__main__":
    main()
