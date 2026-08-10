# Quanta

**Version:** see [`VERSION`](VERSION) (current release tagged `v1.0.0`).

Local Streamlit app for **Gaussian 09** DFT jobs (Windows), portable archives, and **XPS** analysis (Windows + Mac).

Method target: Yamada & Sato, *TANSO* 2015 (`EXample_XPS.pdf`) — OPT B3LYP/6-31G(d), `pop=full`, core MO → C/N/O spectra.

## Agent / architecture kit

See [docs/AI-deployment/](docs/AI-deployment/) — deploy checklist and Streamlit playbooks.  
Product choices: [docs/DECISIONS.md](docs/DECISIONS.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

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
2. **Results** → “Curate fixtures/melanine…”
3. Inspect SCF chart, core table, C/N XPS plots

## Layout

Job files: `data/jobs/<id>/{input,raw,curated,logs}/`  
DB: `data/quanta.db` (gitignored)

## Versioning

- Source of truth: root `VERSION`
- Git tags: `vMAJOR.MINOR.PATCH`
- History: [`CHANGELOG.md`](CHANGELOG.md)
- GitHub: https://github.com/cyril-ver-mar/quanta
