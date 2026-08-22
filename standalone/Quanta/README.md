# Quanta — standalone install

End-user copy of Quanta (Gaussian 09 · ΔSCF XPS).  
Unpack the full standalone zip so this folder contains `app.py`, `src/`, `pages/`, and these scripts.

## Install

| Platform | Command |
|----------|---------|
| macOS / Linux | `./install.sh` |
| Windows | `install.bat` |

Requires **Python 3.11** on PATH.

## Run

| Platform | Command |
|----------|---------|
| macOS / Linux | `./run.sh` |
| Windows | `run.bat` |

If the browser does not open: http://localhost:8501

## Notes

- **Windows:** set the Gaussian executable path on the Settings page to run calculations.
- **macOS:** analyze-only mode (import archives / parse logs) unless Gaussian is installed locally.
