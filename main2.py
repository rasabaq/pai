import json
from pathlib import Path
from comp_fuego import fuego
from comp_bombero import bombero as Bombero
from heuristica import paredes
from loader import data_carga
from simulation import Simulation

INPUT_PATH = "input.dat"
HTML_PATH = Path("visualizacion.html")


def _snapshot(area) -> dict[str, object]:
    """Captures the current state of the grid plus basic counters."""
    grid = [[cell.value for cell in row] for row in area.matrix]
    libres, quemadas, cortafuegos = area.counts()
    return {
        "tick": area.tick,
        "grid": grid,
        "counts": {
            "libres": libres,
            "quemadas": quemadas,
            "cortafuegos": cortafuegos,
        },
    }


def _build_html(history: list[dict[str, object]], report: dict[str, object], n: int) -> str:
    history_json = json.dumps(history, ensure_ascii=False)
    report_json = json.dumps(report, ensure_ascii=False)
    last_stage = len(history) - 1
    initial_counts = history[0]["counts"]
    initial_tick = history[0]["tick"]

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <title>Panel del Bombero</title>
    <style>
        :root {{
            color-scheme: dark;
            font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
            --bg: #05060a;
            --panel: #0f172a;
            --panel-alt: #111827;
            --text: #f8fafc;
            --muted: #94a3b8;
            --accent: #38bdf8;
            --accent-strong: #f97316;
            --stroke: rgba(148, 163, 184, 0.18);
            --c-libre: #1e293b;
            --c-fuego: #fb7185;
            --c-cf: #22d3ee;
            --c-bombero: #c084fc;
        }}
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            min-height: 100vh;
            background: radial-gradient(circle at top, #0b1120, #04050a 60%);
            color: var(--text);
            display: flex;
            flex-direction: column;
            gap: 1.2rem;
            padding: clamp(1.5rem, 3vw, 3rem);
        }}
        .panel {{
            background: var(--panel);
            border-radius: 18px;
            padding: 1.5rem;
            border: 1px solid var(--stroke);
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.35);
        }}
        .intro {{
            color: var(--muted);
            font-size: 0.95rem;
            margin: 0;
        }}
        h2 {{
            margin: 0;
            font-size: 1.2rem;
            letter-spacing: 0.01em;
        }}
        .panel-head {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        .chip {{
            border: 1px solid var(--stroke);
            padding: 0.2rem 0.9rem;
            border-radius: 999px;
            font-size: 0.85rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}
        label {{
            font-size: 0.9rem;
            color: var(--muted);
        }}
        .controls {{
            display: flex;
            flex-direction: column;
            gap: 0.9rem;
        }}
        .controls input[type="range"] {{
            appearance: none;
            width: 100%;
            height: 4px;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.25);
        }}
        .controls input[type="range"]::-webkit-slider-thumb {{
            appearance: none;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: var(--accent);
            box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.25);
        }}
        .controls input[type="range"]::-moz-range-thumb {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            border: none;
            background: var(--accent);
            box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.25);
        }}
        button {{
            border: 1px solid var(--accent);
            background: transparent;
            color: var(--text);
            padding: 0.6rem 1.2rem;
            border-radius: 999px;
            font-size: 0.95rem;
            cursor: pointer;
            width: fit-content;
            transition: background 0.2s ease, color 0.2s ease;
        }}
        button:hover {{
            background: rgba(56, 189, 248, 0.1);
        }}
        #stage-info {{
            font-size: 0.85rem;
            color: var(--muted);
        }}
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            margin-top: 1rem;
            font-size: 0.85rem;
            color: var(--muted);
        }}
        .legend span {{
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .legend i {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid var(--stroke);
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat({n}, minmax(0, 20px));
            gap: 3px;
            justify-content: start;
        }}
        .cell {{
            width: 100%;
            aspect-ratio: 1 / 1;
            border-radius: 4px;
            border: 1px solid rgba(148, 163, 184, 0.1);
            transition: transform 0.15s ease;
        }}
        .cell[data-state="*"] {{ background: var(--c-libre); }}
        .cell[data-state="-"] {{ background: var(--c-fuego); }}
        .cell[data-state="+"] {{ background: var(--c-cf); }}
        .cell[data-state="x"] {{ background: var(--c-bombero); }}
        .report {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 0.8rem;
        }}
        .report-card {{
            background: var(--panel-alt);
            border-radius: 14px;
            padding: 1rem;
            border: 1px solid var(--stroke);
        }}
        .report-card small {{
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 0.05em;
            color: var(--muted);
        }}
        .report-card strong {{
            display: block;
            font-size: 1.4rem;
            margin-top: 0.4rem;
        }}
        @media (max-width: 600px) {{
            body {{
                padding: 1.25rem;
            }}
            .grid {{
                grid-template-columns: repeat({n}, minmax(0, 16px));
                gap: 2px;
            }}
        }}
    </style>
</head>
<body>
    <div class="panel">
        <p class="intro">Explora cada etapa para observar el avance del fuego y la respuesta del cortafuego sin distracciones.</p>
    </div>

    <div class="panel">
        <div class="controls">
            <label for="stage-slider">Etapa <span id="stage-label">0 / {last_stage}</span></label>
            <input id="stage-slider" type="range" min="0" max="{last_stage}" value="0" step="1" />
            <button id="play-btn">Reproducir</button>
            <div id="stage-info">Tick {initial_tick} | Libres {initial_counts['libres']} | Fuego {initial_counts['quemadas']} | Cortafuego {initial_counts['cortafuegos']}</div>
        </div>
        <div class="legend">
            <span><i style="background: var(--c-libre);"></i>Sin afectar</span>
            <span><i style="background: var(--c-fuego);"></i>Fuego</span>
            <span><i style="background: var(--c-cf);"></i>Cortafuego</span>
            <span><i style="background: var(--c-bombero);"></i>Bombero</span>
        </div>
    </div>

    <div class="panel">
        <div id="grid" class="grid" role="presentation" aria-live="polite"></div>
    </div>

    <div class="panel">
        <div class="panel-head">
            <h2>Estado por etapa</h2>
            <span class="chip" id="stage-state">Inicio</span>
        </div>
        <div id="report">
            <!-- Datos del resumen se llenan via JS -->
        </div>
    </div>

    <script type="application/json" id="sim-data">{history_json}</script>
    <script type="application/json" id="report-data">{report_json}</script>
    <script>
        const STAGES = JSON.parse(document.getElementById("sim-data").textContent);
        const REPORT = JSON.parse(document.getElementById("report-data").textContent);
        const slider = document.getElementById("stage-slider");
        const label = document.getElementById("stage-label");
        const info = document.getElementById("stage-info");
        const grid = document.getElementById("grid");
        const playBtn = document.getElementById("play-btn");
        const reportContainer = document.getElementById("report");
        const stageState = document.getElementById("stage-state");
        const FINAL_STAGE = STAGES.length - 1;

        function describeState(stageIndex) {{
            if (stageIndex === FINAL_STAGE) {{
                return REPORT.estado;
            }}
            return stageIndex === 0 ? "Inicio" : "En progreso";
        }}

        function renderReport(stageIndex, stage) {{
            const estado = describeState(stageIndex);
            const cerrado = stageIndex === FINAL_STAGE ? REPORT.cerrado_text : "Pendiente";
            stageState.textContent = estado;
            reportContainer.innerHTML = `
                <div class="report">
                    <div class="report-card">
                        <small>Tick</small>
                        <strong>${{stage.tick}}</strong>
                    </div>
                    <div class="report-card">
                        <small>Etapa</small>
                        <strong>${{stageIndex}} / ${{FINAL_STAGE}}</strong>
                    </div>
                    <div class="report-card">
                        <small>Libres</small>
                        <strong>${{stage.counts.libres}}</strong>
                    </div>
                    <div class="report-card">
                        <small>Fuego</small>
                        <strong>${{stage.counts.quemadas}}</strong>
                    </div>
                    <div class="report-card">
                        <small>Cortafuego</small>
                        <strong>${{stage.counts.cortafuegos}}</strong>
                    </div>
                    <div class="report-card">
                        <small>Cortafuego cerrado</small>
                        <strong>${{cerrado}}</strong>
                    </div>
                </div>
            `;
        }}

        function renderStage(stageIndex) {{
            const stage = STAGES[stageIndex];
            grid.innerHTML = "";
            stage.grid.forEach(row => {{
                row.forEach(cell => {{
                    const div = document.createElement("div");
                    div.className = "cell";
                    div.dataset.state = cell;
                    grid.appendChild(div);
                }});
            }});
            label.textContent = `${{stageIndex}} / ${{FINAL_STAGE}}`;
            info.textContent = `Tick ${{stage.tick}} | Libres ${{stage.counts.libres}} | Fuego ${{stage.counts.quemadas}} | Cortafuego ${{stage.counts.cortafuegos}}`;
            renderReport(stageIndex, stage);
        }}

        let playing = false;
        let timer = null;

        function togglePlay(forceStop = false) {{
            if (forceStop) {{
                playing = false;
            }} else {{
                playing = !playing;
            }}
            playBtn.textContent = playing ? "Pausar" : "Reproducir";
            if (playing) {{
                timer = setInterval(() => {{
                    let next = Number(slider.value) + 1;
                    if (next > Number(slider.max)) {{
                        next = 0;
                    }}
                    slider.value = next;
                    renderStage(next);
                }}, 900);
            }} else if (timer) {{
                clearInterval(timer);
                timer = null;
            }}
        }}

        slider.addEventListener("input", () => {{
            if (playing) {{
                togglePlay(true);
            }}
            renderStage(Number(slider.value));
        }});

        playBtn.addEventListener("click", () => togglePlay());

        renderStage(0);
    </script>
</body>
</html>
"""


def main() -> None:
    n, _, (bi, bj), area = data_carga(INPUT_PATH)
    fire = fuego(tasa_crecimiento=1)
    bomber = Bombero(bi, bj, estrategia=paredes())
    sim = Simulation(area, fire, bomber)

    history = [_snapshot(area)]
    max_steps = 10_000
    steps = 0

    while steps < max_steps:
        if sim._no_more_expansion_after_bomber():
            break
        sim.step()
        steps += 1
        history.append(_snapshot(area))

    finished = len(fire.a_quemar(area)) == 0
    cerrado = area.limite()
    libres, quemadas, cortafuegos = area.counts()
    report = {
        "tick": area.tick,
        "estado": "Finalizada" if finished else "Parcial",
        "cerrado": cerrado,
        "cerrado_text": "Si" if cerrado else "No",
        "counts": {
            "libres": libres,
            "quemadas": quemadas,
            "cortafuegos": cortafuegos,
        },
    }

    html = _build_html(history, report, n)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"[OK] Visualizacion generada en {HTML_PATH} ({len(history)} etapas).")


if __name__ == "__main__":
    main()
