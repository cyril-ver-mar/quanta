# Quanta

**Version:** see [`VERSION`](VERSION).

Local Streamlit app for **Gaussian 09** DFT jobs (Windows) and **ΔSCF XPS** analysis (Windows + Mac).

## Install / run

**macOS / Linux**

```bash
./install.sh
./run.sh
```

**Windows**

```bat
install.bat
run.bat
```

Open http://localhost:8501

Activate `venv` in every new terminal before manual commands.

## Modes

| Machine | Gaussian configured | What works |
|---------|---------------------|------------|
| Windows | yes | queue + analyze + export archive |
| Mac / no `g09` | no | import archive + analyze logs / XPS |

## First check (no Gaussian)

1. `./run.sh`
2. **Compounds** → add a test molecule (or melanine fixture)
3. **Results** → inspect energies / XPS plots when a job has finished

## Layout

```text
app.py, launch.py, pages/   # Streamlit UI
src/                        # core, services, db, ui helpers
tests/                      # pytest
scripts/build_standalone.py # build end-user zip locally (not in git)
fixtures/                   # sample inputs
docs/                       # DECISIONS, ARCHITECTURE
```

Job files: `data/jobs/<id>/{input,raw,curated,logs}/`  
DB: `data/quanta.db` (gitignored)

## End-user package

This repository is **source only**. To build a clean installable folder:

```bash
python scripts/build_standalone.py
# → standalone/Quanta/  (gitignored; zip and attach to a GitHub Release)
```

## Docs

- Product choices: [`docs/DECISIONS.md`](docs/DECISIONS.md)
- Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Versioning

- Source of truth: root `VERSION`
- Git tags: `vMAJOR.MINOR.PATCH`
- History: [`CHANGELOG.md`](CHANGELOG.md)
- GitHub: https://github.com/cyril-ver-mar/quanta
