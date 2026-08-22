# Quanta

Gaussian 09 DFT jobs and **ΔSCF XPS** analysis (gas-phase molecules).

## Install & run

### macOS / Linux

```bash
./install.sh
./run.sh
```

### Windows

```bat
install.bat
run.bat
```

Open in browser: http://localhost:8501  
If the browser does not open automatically, paste the URL manually.

## Workflow

1. **Settings** — Gaussian path (Windows), functional, FWHM  
2. **Compounds** — import mol2 / pdb / sdf  
3. **Work review** — check 3D structure  
4. **Jobs** — create ΔSCF workflow  
5. **Queue** — run Gaussian steps  
6. **Results** — binding energies and spectra  

Requires **Python 3.11**.

## Secrets (optional)

Copy `SECRETS.example` → `SECRETS` next to `app.py` and add:

```
GITHUB_TOKEN=ghp_your_token
```

This raises GitHub update-check rate limits. Keep `SECRETS` private; you may copy it between trusted machines. In-app updates preserve `SECRETS`.
