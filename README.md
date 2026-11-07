# analista-inteligencia

Le das un tema ("Rappi en Colombia") y entrega un **informe de inteligencia competitiva** en
HTML, Markdown y JSON donde **cada cita fue comprobada por código contra la página original**.
Hecho con el [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk).

## Cómo correrlo

```bash
uv sync                                   # solo la primera vez
uv run agente.py                          # prueba: Rappi en Colombia
uv run agente.py "Nubank en México"       # tu tema
xdg-open workspace/entregas/informe.html  # ver el informe (Mac: open · Windows: start)
uv run evals/correr_evals.py 2            # puntaje 0-100 en 2 temas
```

Credencial: `.env` con `AGENTE_AUTH=api_key` (ver `.env.example`). Nunca subas `.env` a git.

## Cómo funciona

```
tú: "Rappi en Colombia"
      │
      ▼
┌─ coordinador · Sonnet 5.5 · skill «investigar-competidor» ───────────────┐
│ 1. mcp__vigia__fecha_hoy + ya_visto("*")         ← memoria entre corridas │
│ 2. Agent ×3 EN PARALELO → investigador (Haiku 5.5): noticias/negocio/producto│
│       WebSearch · WebFetch · ya_visto                                     │
│ 3. Agent → verificador (Sonnet 5.5) → mcp__vigia__verificar_cita          │
│       descarga la página y busca la cita LITERAL (código, no IA)          │
│ 4. Write entregas/informe.json → Bash render_html.py → .html + .md        │
│ 5. mcp__vigia__registrar cada fuente                                      │
└───────────────────────────────────────────────────────────────────────────┘
 vigilantes (hooks.py):
   PreToolUse·Bash  → sin sudo, sin borrar /, ~ ni nada fuera del proyecto
   PostToolUse      → salidas/auditoria.jsonl (quién usó qué)
   Stop             → NO deja terminar si alguna cita no está verificada
 frenos: max_turns=40 · max_budget_usd=2.50
```

## Qué lo hace distinto

| Mejora | Dónde |
|---|---|
| Investigadores en paralelo con modelo barato | `agents=` en `agente.py` |
| Verificación determinista de citas | `herramientas.py` → `verificar_cita` |
| El agente no puede entregar citas falsas | `hooks.py` → `exigir_citas_verificadas` |
| Memoria: la 2ª corrida marca solo lo NUEVO | `workspace/datos/memoria.json` |
| Tablero HTML con indicadores (modo oscuro incluido) | skill → `scripts/render_html.py` |
| Bitácora auditable | `salidas/auditoria.jsonl` |
| Evals con puntaje y re-verificación independiente | `evals/` |
| Defensa contra prompt injection de páginas web | system prompts |

## Cuánto cuesta

Prueba real (2026-11-07, Rappi en Colombia): **$0.49**, unos 3 minutos, 8 hallazgos verificados.
Tope duro: $2.50 por informe.

## Archivos

| Archivo | Qué es |
|---|---|
| `agente.py` | coordinador, subagentes y todas las decisiones en un bloque |
| `herramientas.py` | servidor MCP en proceso `vigia` (fecha, memoria, verificación) |
| `hooks.py` | los tres vigilantes |
| `credenciales.py` | lee `.env` y deja una sola credencial |
| `workspace/.claude/skills/investigar-competidor/` | procedimiento, metodología y script HTML |
| `evals/` | casos, script de puntaje y resultados |
| `decisiones.md` | por qué cada decisión |

## Si algo falla

| Lo que ves | Qué pasa |
|---|---|
| `[auth] Falta …` | `.env` incompleto |
| `401` / `Invalid API key` | la key no sirve: crea otra en platform.claude.com/settings/keys |
| `error_max_budget_usd` | tocó el tope: sube `max_budget_usd` |
| `🛑 hook Stop` | normal: el agente corrige citas antes de entregar |
| `no_accesible` en citas | la página bloquea robots; el agente busca otra fuente |
