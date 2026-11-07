# hooks.py — paso 9: los vigilantes. Código TUYO que corre antes que cualquier permiso.
#
# 1. no_borrar_el_sistema  (PreToolUse · Bash)  → la ÚNICA limitación de la terminal:
#    nada de sudo ni de borrar /, tu carpeta personal o algo fuera del proyecto.
# 2. bitacora              (PostToolUse · todas) → salidas/auditoria.jsonl, sin frenar nada.
# 3. exigir_citas_verificadas (Stop)            → el agente NO puede terminar mientras el
#    informe tenga una cita que verificar_cita no confirmó. Anti-alucinaciones con un `if`.
#
# TRAMPA: las claves de salida van en camelCase también en Python (hookSpecificOutput,
# permissionDecision…). Una clave en snake_case se ignora en silencio.

import asyncio
import json
import os
import re
import shlex
import time
from pathlib import Path
from typing import Any

from herramientas import VERIFICACIONES, clave_cita

PROYECTO = Path(__file__).resolve().parent


# ─── 1 · No borrar el sistema ─────────────────────────────────────────────

SIEMPRE_PROHIBIDO = [
    (r"(^|[;&|\s(])sudo\b", "sudo"),
    (r"(^|[;&|\s(])su\s", "su"),
    (r"\bmkfs", "mkfs"),
    (r"\bdd\s+[^|;&]*of=/dev/", "dd sobre un disco"),
    (r":\(\)\s*\{", "fork bomb"),
    (r">\s*/dev/sd", "escribir sobre un disco"),
    (r"\bchmod\s+-R\s+\S+\s+/(\s|$)", "chmod recursivo en /"),
    (r"\bchown\s+-R\s+\S+\s+/(\s|$)", "chown recursivo en /"),
    (r"--no-preserve-root", "--no-preserve-root"),
]


def _ruta_peligrosa(arg: str, cwd: Path) -> bool:
    """True si borrar `arg` tocaría algo fuera del proyecto (o el proyecto entero)."""
    if arg in ("*", ".", "..", "~", "/") or arg.startswith(("~", "$HOME", "${HOME}", "$")):
        return True
    destino = Path(os.path.expanduser(arg))
    destino = (destino if destino.is_absolute() else cwd / destino).resolve()
    return destino == PROYECTO or not destino.is_relative_to(PROYECTO)


def _rm_peligroso(comando: str, cwd: Path) -> str | None:
    for trozo in re.split(r"&&|\|\||;|\||\n", comando):
        try:
            partes = shlex.split(trozo)
        except ValueError:
            partes = trozo.split()
        if not partes:
            continue
        nombre = Path(partes[0]).name
        if nombre in ("rm", "shred", "rmdir") or partes[:2] == ["find", "/"] and "-delete" in partes:
            rutas = [p for p in partes[1:] if not p.startswith("-")]
            if nombre == "find" or any(_ruta_peligrosa(r, cwd) for r in rutas):
                return trozo.strip()
    return None


def _negar(input_data: dict[str, Any], motivo: str) -> dict[str, Any]:
    return {
        "systemMessage": f"🛡️  hook bloqueó: {motivo}",          # lo lee la persona
        "hookSpecificOutput": {
            "hookEventName": input_data["hook_event_name"],
            "permissionDecision": "deny",
            "permissionDecisionReason": (                         # lo lee el modelo
                f"Bloqueado por política ({motivo}). No uses sudo ni borres fuera de la carpeta "
                "del proyecto. Si necesitas limpiar, borra solo archivos concretos dentro de "
                "workspace/ o sigue sin borrar."
            ),
        },
    }


async def no_borrar_el_sistema(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
    comando = input_data.get("tool_input", {}).get("command", "")
    cwd = Path(input_data.get("cwd") or PROYECTO).resolve()
    for patron, nombre in SIEMPRE_PROHIBIDO:
        if re.search(patron, comando):
            return _negar(input_data, nombre)
    if trozo := _rm_peligroso(comando, cwd):
        return _negar(input_data, f"borrado fuera del proyecto: {trozo[:60]}")
    return {}   # sin opinión: que siga


# ─── 2 · Bitácora de todo ─────────────────────────────────────────────────

BITACORA = PROYECTO / "salidas" / "auditoria.jsonl"


def _escribir(registro: dict[str, Any]) -> None:
    BITACORA.parent.mkdir(exist_ok=True)
    with BITACORA.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")


async def bitacora(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
    registro = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "session_id": input_data.get("session_id"),
        "agente": input_data.get("agent_id") or "coordinador",
        "tool": input_data.get("tool_name"),
        "input": input_data.get("tool_input"),
    }
    try:
        await asyncio.to_thread(_escribir, registro)
    except Exception as e:  # noqa: BLE001 — la bitácora nunca tumba al agente
        print("fallo escribiendo bitácora:", e)
    return {"async_": True, "asyncTimeout": 5000}


# ─── 3 · No termina con citas sin verificar ───────────────────────────────

INFORME = Path("entregas") / "informe.json"     # relativo al cwd del agente
VALIDAS = {"verificada", "parcial"}


def revisar_informe(ruta: Path) -> list[str]:
    """Lista de problemas del informe. Vacía = aprobado. La usan el hook y los evals."""
    if not ruta.exists():
        return [f"no existe {INFORME}"]
    try:
        informe = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"{INFORME} no es JSON válido: {e}"]
    problemas = []
    for campo in ("tema", "fecha", "resumen_ejecutivo", "hallazgos"):
        if not informe.get(campo):
            problemas.append(f"falta el campo «{campo}»")
    verif = json.loads(VERIFICACIONES.read_text(encoding="utf-8")) if VERIFICACIONES.exists() else {}
    hallazgos = informe.get("hallazgos") or []
    if len(hallazgos) < 3:
        problemas.append(f"solo hay {len(hallazgos)} hallazgos; se piden al menos 3")
    for i, h in enumerate(hallazgos, 1):
        fuentes = h.get("fuentes") or []
        if not fuentes:
            problemas.append(f"hallazgo {i} «{h.get('titulo', '?')}» no tiene fuentes")
        for f in fuentes:
            estado = verif.get(clave_cita(f.get("url", ""), f.get("cita", "")), {}).get("estado")
            if estado not in VALIDAS:
                problemas.append(
                    f"hallazgo {i}: la cita de {f.get('url', '?')} está «{estado or 'sin verificar'}»"
                )
    return problemas


async def exigir_citas_verificadas(input_data: dict[str, Any], tool_use_id: str | None, context: Any) -> dict[str, Any]:
    if input_data.get("stop_hook_active"):
        return {}   # ya bloqueó una vez en este turno: evita el bucle infinito
    problemas = revisar_informe(Path(input_data.get("cwd") or ".") / INFORME)
    if not problemas:
        print("✅ hook Stop: todas las citas del informe están verificadas")
        return {}
    print(f"🛑 hook Stop: {len(problemas)} problema(s); el agente sigue trabajando")
    return {
        "decision": "block",
        "reason": (
            "Todavía no puedes terminar. Problemas del informe:\n- " + "\n- ".join(problemas[:15]) +
            "\nPara cada cita: pásala por mcp__vigia__verificar_cita con el texto EXACTO de la "
            "página, o elimina esa fuente (y el hallazgo si queda sin fuentes). Luego reescribe "
            "entregas/informe.json y vuelve a generar el HTML."
        ),
    }
