# correr_evals.py — mide al agente con números, no con impresiones.
#
#   uv run evals/correr_evals.py            ← todos los casos (≈ $1-2 por caso)
#   uv run evals/correr_evals.py 2          ← solo los 2 primeros
#
# Puntaje por caso (0-100):
#   40  el informe pasa revisar_informe() — mismo chequeo del hook Stop (citas verificadas)
#   20  tiene al menos min_hallazgos hallazgos
#   15  menciona las palabras clave del tema
#   15  re-verificación independiente: se re-descarga una muestra de citas y deben seguir ahí
#   10  generó informe.html
# Resultado: evals/resultados.md + resultados.json

import asyncio, json, shutil, subprocess, sys, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from hooks import revisar_informe                      # noqa: E402
from herramientas import _descargar, comparar          # noqa: E402

ENTREGAS = RAIZ / "workspace" / "entregas"


def recheck(informe: dict, n: int = 3) -> float:
    citas = [f for h in informe.get("hallazgos", []) for f in h.get("fuentes", [])][:n]
    if not citas:
        return 0.0
    ok = 0
    for f in citas:
        try:
            ok += comparar(_descargar(f["url"]), f["cita"])[0] in ("verificada", "parcial")
        except Exception:
            pass
    return ok / len(citas)


def evaluar(caso: dict) -> dict:
    shutil.rmtree(ENTREGAS, ignore_errors=True); ENTREGAS.mkdir(parents=True)
    t0 = time.time()
    proc = subprocess.run([sys.executable, str(RAIZ / "agente.py"), caso["tema"]],
                          cwd=RAIZ, capture_output=True, text=True, timeout=1200)
    costo = next((float(l.split("$")[1].split()[0]) for l in proc.stdout.splitlines()
                  if " turnos · $" in l), 0.0)
    ruta = ENTREGAS / "informe.json"
    problemas = revisar_informe(ruta)
    informe = json.loads(ruta.read_text()) if ruta.exists() else {}
    texto = json.dumps(informe, ensure_ascii=False).lower()
    hs = informe.get("hallazgos", [])
    rv = recheck(informe)
    puntos = (40 * (not problemas) + 20 * (len(hs) >= caso["min_hallazgos"])
              + 15 * all(p in texto for p in caso["debe_mencionar"]) + round(15 * rv)
              + 10 * (ENTREGAS / "informe.html").exists())
    destino = RAIZ / "evals" / "informes" / caso["tema"].replace(" ", "_")
    if ENTREGAS.exists():
        shutil.copytree(ENTREGAS, destino, dirs_exist_ok=True)
    return {"tema": caso["tema"], "puntaje": puntos, "hallazgos": len(hs), "problemas": problemas[:5],
            "reverificacion": rv, "costo_usd": costo, "segundos": round(time.time() - t0)}


def main() -> None:
    casos = json.loads((RAIZ / "evals" / "casos.json").read_text())
    if len(sys.argv) > 1:
        casos = casos[: int(sys.argv[1])]
    res = []
    for c in casos:
        print(f"▶ {c['tema']} …", flush=True)
        r = evaluar(c); res.append(r)
        print(f"  {r['puntaje']}/100 · {r['hallazgos']} hallazgos · ${r['costo_usd']:.2f} · {r['segundos']}s")
    prom = sum(r["puntaje"] for r in res) / len(res)
    costo = sum(r["costo_usd"] for r in res) / len(res)
    filas = "\n".join(f"| {r['tema']} | {r['puntaje']} | {r['hallazgos']} | {r['reverificacion']:.0%} | "
                      f"${r['costo_usd']:.2f} | {r['segundos']}s |" for r in res)
    md = (f"# Resultados de evals\n\n**Puntaje promedio: {prom:.0f}/100 · costo promedio ${costo:.2f} por informe**\n\n"
          "| Tema | Puntaje | Hallazgos | Re-verificación | Costo | Tiempo |\n|---|---|---|---|---|---|\n" + filas + "\n")
    (RAIZ / "evals" / "resultados.md").write_text(md, encoding="utf-8")
    (RAIZ / "evals" / "resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print("\n" + md)


if __name__ == "__main__":
    main()
