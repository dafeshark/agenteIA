# herramientas.py — paso 5: las funciones PROPIAS del agente (servidor MCP en proceso).
#
# Claude no ejecuta esto: pide la herramienta por su nombre y este programa la corre.
# Nombres que ve el modelo:  mcp__vigia__fecha_hoy · mcp__vigia__ya_visto
#                            mcp__vigia__registrar · mcp__vigia__verificar_cita
#
# La pieza clave es verificar_cita: descarga la página y busca la cita LITERAL con
# código determinista. Un modelo puede inventar una fuente; este `if` no.

import asyncio
import datetime as dt
import html
import json
import re
import unicodedata
import urllib.request
from pathlib import Path
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

DATOS = Path(__file__).resolve().parent / "workspace" / "datos"
MEMORIA = DATOS / "memoria.json"            # lo ya reportado, entre corridas
VERIFICACIONES = DATOS / "verificaciones.json"   # resultado de cada verificar_cita
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/130.0 Safari/537.36")


# ─── utilidades (también las usa hooks.py) ────────────────────────────────

def normalizar(texto: str) -> str:
    """minúsculas, sin tildes, sin puntuación, espacios simples."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    texto = re.sub(r"[^\w\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def clave_cita(url: str, cita: str) -> str:
    return url.strip().rstrip("/") + " | " + normalizar(cita)


def _leer(ruta: Path) -> dict:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _guardar(ruta: Path, datos: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def _texto(contenido: str) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": contenido}]}


def _descargar(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es,en"})
    with urllib.request.urlopen(req, timeout=20) as r:
        crudo = r.read(3_000_000).decode(r.headers.get_content_charset() or "utf-8", "replace")
    crudo = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", crudo)
    return html.unescape(re.sub(r"(?s)<[^>]+>", " ", crudo))


def comparar(pagina: str, cita: str) -> tuple[str, float]:
    """Devuelve (estado, cobertura). verificada = literal; parcial = ≥80% de trigramas."""
    p, c = normalizar(pagina), normalizar(cita)
    if not c:
        return "no_encontrada", 0.0
    if c in p:
        return "verificada", 1.0
    palabras = c.split()
    if len(palabras) < 4:
        return "no_encontrada", 0.0
    tri = [" ".join(palabras[i:i + 3]) for i in range(len(palabras) - 2)]
    cobertura = sum(t in p for t in tri) / len(tri)
    return ("parcial" if cobertura >= 0.8 else "no_encontrada"), round(cobertura, 2)


# ─── las herramientas ─────────────────────────────────────────────────────

@tool("fecha_hoy", "Devuelve la fecha y hora actuales (zona America/Bogota). Pídela siempre; no adivines fechas.", {})
async def fecha_hoy(args: dict[str, Any]) -> dict[str, Any]:
    ahora = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5)))
    return _texto(ahora.strftime("%Y-%m-%d %H:%M (America/Bogota, %A)"))


@tool(
    "ya_visto",
    "Consulta la memoria del vigía: dice si una URL ya fue reportada en una corrida anterior y "
    "cuándo. Con url='*' devuelve las últimas 30 entradas del tema. Úsala antes de reportar algo.",
    {"url": str},
)
async def ya_visto(args: dict[str, Any]) -> dict[str, Any]:
    memoria = _leer(MEMORIA)
    url = args["url"].strip().rstrip("/")
    if url == "*":
        ultimas = sorted(memoria.items(), key=lambda kv: kv[1]["fecha"], reverse=True)[:30]
        if not ultimas:
            return _texto("memoria vacía: es la primera corrida")
        return _texto("\n".join(f"- {v['fecha']} · {v['tema']} · {v['titulo']} · {u}" for u, v in ultimas))
    if url in memoria:
        v = memoria[url]
        return _texto(f"YA REPORTADO el {v['fecha']} (tema: {v['tema']}): {v['titulo']}")
    return _texto("nuevo: nunca se ha reportado")


@tool(
    "registrar",
    "Guarda en la memoria del vigía una fuente que entró al informe final, para no repetirla "
    "como novedad la próxima vez. Llámala una vez por fuente, al final.",
    {"url": str, "titulo": str, "tema": str},
)
async def registrar(args: dict[str, Any]) -> dict[str, Any]:
    memoria = _leer(MEMORIA)
    url = args["url"].strip().rstrip("/")
    memoria[url] = {"titulo": args["titulo"], "tema": args["tema"],
                    "fecha": dt.date.today().isoformat()}
    _guardar(MEMORIA, memoria)
    return _texto(f"registrado ({len(memoria)} fuentes en memoria)")


@tool(
    "verificar_cita",
    "Descarga la URL y comprueba con código (no con IA) que la cita aparece en la página. "
    "Responde verificada (literal), parcial (≥80% coincide) o no_encontrada, o no_accesible si la "
    "página no se pudo bajar. Pasa la cita copiada tal cual de la fuente, 8 a 40 palabras.",
    {"url": str, "cita": str},
)
async def verificar_cita(args: dict[str, Any]) -> dict[str, Any]:
    url, cita = args["url"].strip(), args["cita"].strip()
    try:
        pagina = await asyncio.to_thread(_descargar, url)
        estado, cobertura = comparar(pagina, cita)
    except Exception as e:  # noqa: BLE001 — cualquier fallo de red es un dato, no un crash
        estado, cobertura = "no_accesible", 0.0
        print(f"  >>> verificar_cita: {url} no accesible ({type(e).__name__})")
    registro = _leer(VERIFICACIONES)
    registro[clave_cita(url, cita)] = {"estado": estado, "cobertura": cobertura,
                                       "fecha": dt.datetime.now().isoformat(timespec="seconds")}
    _guardar(VERIFICACIONES, registro)
    print(f"  >>> verificar_cita → {estado} ({cobertura:.0%}) {url[:70]}")
    consejo = {
        "verificada": "Puedes usarla.",
        "parcial": "Úsala copiando el texto exacto de la página si puedes.",
        "no_encontrada": "No la uses: busca la frase exacta en la página o descarta el hallazgo.",
        "no_accesible": "La página bloquea descargas: busca otra fuente para el mismo dato.",
    }[estado]
    return _texto(f"{estado} (cobertura {cobertura:.0%}). {consejo}")


vigia = create_sdk_mcp_server(
    name="vigia", version="1.0.0",
    tools=[fecha_hoy, ya_visto, registrar, verificar_cita],
)
