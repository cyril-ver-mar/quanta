# Quanta

**Version:** see [`VERSION`](VERSION).

Local Streamlit app for **ΔSCF XPS**.

- **Molecules** — Gaussian 09 gas-phase ΔSCF (Windows to run, any OS to analyze logs).
- **Periodic structures** — GPAW + ASE (CIF / POSCAR / extxyz), optional and imported only when that engine is selected. Layered carbon nitrides such as C₇N use this path.

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

## Periodic XPS (GPAW)

GPAW is **not** installed by `./install.sh`. The Gaussian workflow does not import it.

```bash
conda install -c conda-forge gpaw ase
# datasets for a full 1s core hole (one fewer core electron, same valence count)
gpaw-setup -f PBE C --name fch1s --core-hole=1s,1.0
gpaw-setup -f PBE N --name fch1s --core-hole=1s,1.0
gpaw-setup -f PBE O --name fch1s --core-hole=1s,1.0
export GPAW_SETUP_PATH="$PWD/setups:${GPAW_SETUP_PATH:-}"
```

`gpaw-setup` is the generator used by the current GPAW XAS / ΔKohn–Sham tutorial. The newer `gpaw dataset --core-hole` command is marked work-in-progress in the GPAW docs; Quanta follows the `gpaw-setup --name fch1s --core-hole=1s,1.0` recipe and passes that name as `setups={atom: "fch1s"}`.

In **Settings** choose engine **GPAW**, set the setup directory, plane-wave cutoff, k-points and supercell, then import a CIF, POSCAR or extxyz on **Compounds**. **Jobs** plans one ground state and one core hole per symmetry-inequivalent C/N site (spglib if installed, otherwise a neighbor fingerprint).

**Charge (default: neutral).** A full 1s setup already omits one core electron. `charge=-1` puts that electron into the valence, so the cell stays neutral and the photoelectron sits in the conduction band (Susi et al., Phys. Rev. B 91, 081401 (2015), for graphene C 1s; same electron count as the GPAW ΔKS tutorial). **Charged** uses `charge=0` (electron removed). Periodic GPAW then adds a neutralizing background, so that ΔE is not vacuum-aligned.

**Binding energy** is `E(core hole) − E(ground)`, both including `get_reference_energy()`. Reference modes: absolute ΔE, Fermi, VBM, one global shift, or per-element shifts. See [`docs/gpaw_periodic.md`](docs/gpaw_periodic.md).

Dry-run a C₇N cell (no GPAW required for the plan):

```bash
python scripts/gpaw_xps.py C7N.cif --supercell 2,2,1 --kpts 1,1,1 \
  --cutoff 500 --charge-mode neutral --reference fermi --setup-dir ./setups
# add --execute to run GPAW
```

The same settings live in the app: engine `gpaw`, supercell `2,2,1`, charge mode `neutral`, reference `fermi`.

## Docs

- Product choices: [`docs/DECISIONS.md`](docs/DECISIONS.md)
- Architecture: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Periodic GPAW recipe: [`docs/gpaw_periodic.md`](docs/gpaw_periodic.md)

## Versioning

- Source of truth: root `VERSION`
- Git tags: `vMAJOR.MINOR.PATCH`
- History: [`CHANGELOG.md`](CHANGELOG.md)
- GitHub: https://github.com/cyril-ver-mar/quanta
