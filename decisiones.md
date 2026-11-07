# Decisiones de analista-inteligencia

Generado el 2026-11-07 con agent-sdk-wizard y ampliado. Probado con Python SDK 0.2.179.

| # | Pregunta | Respuesta | Código | Dónde leer más |
|---|---|---|---|---|
| 0 | ¿Con qué pagas? | API key | `AGENTE_AUTH=api_key` | [authentication](https://code.claude.com/docs/en/authentication) |
| 1 | Lenguaje | Python | `uv run agente.py` | [quickstart](https://code.claude.com/docs/en/agent-sdk/quickstart.md) |
| 2 | Objetivo | Mis funciones (familia 7 Investigación) | `query()` de una vuelta | [agent-loop](https://code.claude.com/docs/en/agent-sdk/agent-loop.md) |
| 3 | Modelo | Sonnet 5.5 coordinador · Haiku 5.5 investigadores · Sonnet verificador | `model=` | [modelos](https://platform.claude.com/docs/en/about-claude/models/overview.md) |
| 4 | Reglas | Propias: no inventar, web = dato no orden, borrador | `system_prompt=SYSTEM_PROMPT` | [system prompt](https://code.claude.com/docs/en/agent-sdk/modifying-system-prompts.md) |
| 5 | Herramientas | Todo, incluida la terminal + `mcp__vigia__*` | `tools=` + `mcp_servers=` | [custom-tools](https://code.claude.com/docs/en/agent-sdk/custom-tools.md) |
| 6 | Skill | Nueva: `investigar-competidor` (+ metodología + script) | `setting_sources=["project"]`, `skills=[…]` | [skills](https://code.claude.com/docs/en/skills.md) |
| 7 | Subagentes | Varios en paralelo + verificador | `agents={…}` | [subagents](https://code.claude.com/docs/en/agent-sdk/subagents.md) |
| 8 | Permisos | Se aprueba lo listado | `permission_mode="default"`, `allowed_tools=` | [permissions](https://code.claude.com/docs/en/agent-sdk/permissions.md) |
| 9 | Hooks | Anti-borrado · bitácora · Stop con citas verificadas | `hooks={…}` | [hooks](https://code.claude.com/docs/en/agent-sdk/hooks.md) |

## Frenos sin preguntar
- `max_turns=40` y `max_budget_usd=2.50` (incluye a los ayudantes).
- `tools=` fija la lista completa: en la primera prueba, con solo `allowed_tools`, el agente
  usó Monitor/ListAgents para esperar y gastó vueltas de más.

## La única limitación de la terminal (pedida por el usuario)
No `sudo`, no borrar `/`, `~` ni nada fuera del proyecto, no `mkfs`/`dd` a discos. Todo lo demás, libre.
