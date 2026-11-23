# Periodic ΔSCF XPS with GPAW

Quanta uses this path for crystals and layered materials (carbon nitrides such as C₇N). Molecules stay on Gaussian 09.

The calculator arguments follow the GPAW ΔKohn–Sham example in the XAS tutorial (`charge`, `spinpol`, `FermiDirac(..., fixmagmom=True)`, `setups={index: name}`, `get_potential_energy() + get_reference_energy()`) and the neutral supercell of Susi et al., Phys. Rev. B **91**, 081401 (2015).

## Install

GPAW is optional. The Gaussian pages do not import it.

```bash
conda install -c conda-forge gpaw ase
```

Generate a **full 1s** dataset (occupation of the 1s shell reduced by 1). The tutorial’s name `fch1s` is what Quanta looks up:

```bash
mkdir -p setups
cd setups
gpaw-setup -f PBE C --name fch1s --core-hole=1s,1.0
gpaw-setup -f PBE N --name fch1s --core-hole=1s,1.0
gpaw-setup -f PBE O --name fch1s --core-hole=1s,1.0
cd ..
export GPAW_SETUP_PATH="$PWD/setups:${GPAW_SETUP_PATH:-}"
```

Put that directory in **Settings → GPAW → setup directory** as well (Quanta calls `setup_paths.insert`).

The current GPAW documentation also mentions `gpaw dataset --core-hole`, and labels that generator as work in progress. Quanta does not call it. Use `gpaw-setup`, which is the generator the XAS tutorial and the distributed setups are built with.

Reading a CIF / POSCAR / extxyz needs ASE (`conda install ase` or `pip install ase`). Running the SCF needs GPAW.

## Charge

A full 1s dataset has one fewer **core** electron and the same valence count as the ordinary setup.

| Mode | GPAW `charge` | What it is |
|------|----------------|------------|
| **neutral (default)** | `-1` | The core electron is placed in the valence. The cell is neutral; the extra electron sits in the conduction band. Spin-polarized, magnetic moment 1 on the excited atom, `FermiDirac(width, fixmagmom=True)`. |
| **charged** | `0` | The core electron is removed and not put back. Under periodic boundary conditions GPAW adds a uniform background. The raw ΔE is not aligned to vacuum. |

`width` is the Fermi–Dirac smearing in eV. GPAW’s own default for a periodic calculation is 0.1 eV (0 for a molecule); Quanta uses 0.1 and exposes it in Settings. The XAS tutorial’s molecular example uses `FermiDirac(0.0, fixmagmom=True)`. Plane-wave cutoff (`mode=PW(cutoff)`, starting value 500 eV) and the k-point mesh are the same kind of input: documented GPAW parameters, not values that have been converged for C₇N.

## Binding energy

```text
BE_raw = [E(core hole) + E_ref(core hole)] − [E(ground) + E_ref(ground)]
```

GPAW totals are already in eV.

| Reference | Neutral cell | Charged cell |
|-----------|----------------|--------------|
| absolute | `BE_raw` | `BE_raw` |
| fermi | `BE_raw` (the photoelectron is at the band edge; for a metal this is the Fermi level, as in Susi et al.) | `BE_raw − ε_F` of the ground state. Background charge is still present. |
| vbm | `BE_raw + (ε_CBM − ε_VBM)` using **ground-state** edges only | `BE_raw − ε_VBM` |
| global / per element | same shifts as in the molecular workflow, applied to `BE_raw` | same |

VBM is the highest ground-state eigenvalue that is at least half occupied. CBM is the lowest that is not. If GPAW did not compute an empty band, VBM mode cannot add a gap.

## C₇N workflow

The structure file is not in the repository. Any CIF, POSCAR or extxyz with a cell is accepted.

1. Generate C and N `fch1s` setups (above) and set `GPAW_SETUP_PATH`.
2. **Settings:** engine GPAW, elements `C,N`, setup name `fch1s`, charge mode **neutral**, reference **fermi** (or **vbm** if you want the gap added).
3. Choose a supercell. `1,1,1` is only a smoke test: core-hole images interact. For a layered cell, start from something like `2,2,1` or `3,3,1` and check that the BEs stop changing.
4. **Compounds** → upload `C7N.cif` (or `POSCAR` renamed `C7N.poscar` / `C7N.vasp`).
5. **Jobs** → create the workflow. Quanta keeps one atom per symmetry class (spglib if it is installed, otherwise a minimum-image neighbor fingerprint) and weights the spectrum by how many atoms that class contains.
6. **Queue** → run. Each step writes a `.py` file under `data/jobs/<id>/input/` that is the same GPAW call the runner makes.
7. **Results** → table and broadened C 1s / N 1s spectra.

Command-line equivalent:

```bash
python scripts/gpaw_xps.py C7N.cif \
  --supercell 2,2,1 \
  --kpts 1,1,1 \
  --cutoff 500 \
  --charge-mode neutral \
  --reference fermi \
  --elements C,N \
  --setup-name fch1s \
  --setup-dir ./setups
# plan only; add --execute to run GPAW
```

A small CN layer used by the unit tests is `fixtures/periodic/cn_layer.extxyz`.

## What this does not do

- No geometry optimization. The calculation uses the geometry in the file.
- No automatic charged-cell correction (Makov–Payne, potential alignment, vacuum level).
- The neutral-cell VBM shift is `gap = ε_CBM − ε_VBM` of the ground state. It assumes the extra electron sits at the CBM. It is not a substitute for a slab vacuum reference.
- Symmetry of the core-hole calculation is turned off (`symmetry={'point_group': False, 'time_reversal': False}`) so the hole is not copied onto equivalent atoms. The ground state keeps GPAW’s default symmetry.
- Core-hole datasets are not shipped. Without `fch1s` for every element you excite, GPAW will not find the setup.
- ORCA is not implemented. A later engine should plan `DscfStep`s and register a runner next to `GaussianRunner` and `GpawRunner`.
