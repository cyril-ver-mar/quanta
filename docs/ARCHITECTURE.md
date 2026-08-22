# Quanta — architecture

See also [`docs/DECISIONS.md`](DECISIONS.md).

## Run

```bash
./install.sh   # once
./run.sh       # → http://localhost:8501
```

Windows: `install.bat` / `run.bat`.

## Folder map

```text
app.py / launch.py / pages/
src/utils/      # paths, config, cancel, i18n, logging
src/core/       # domain models, XPS math, Gaussian input text
src/db/         # SQLite schema + repositories
src/services/   # compounds, jobs, runner, parser, XPS, archive
src/ui/         # thin Streamlit components
scripts/        # build_standalone.py (local end-user zip)
data/           # runtime (gitignored): quanta.db, jobs/, cancel flags
fixtures/       # melanine sample .gjf / .LOG
exports/        # portable archives
docs/           # DECISIONS, ARCHITECTURE, Instruction snapshots
```

## Import direction

`pages/ui → services → db → core → utils`

## Modes

| Mode | When | Capabilities |
|------|------|----------------|
| `run` | Gaussian executable configured and found | queue + analyze |
| `analyze` | Mac / no Gaussian | import archive, parse logs, XPS plots |
