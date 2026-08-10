# Playbook 08 — Testing

**Checklist ID:** F1  
**Ask user:** implement yes / no / later?

## Goal

Fast feedback for domain + services; optional UI smoke.

## Pattern

```bash
./venv/bin/python -m pytest tests/ -q -m "not slow"
```

- Unit-test `core` and `services` without Streamlit when possible.  
- Mark heavy tests `@pytest.mark.slow`.  
- Optional: Streamlit `AppTest` for critical pages.  

## Templates

`TEMPLATES/tests/test_smoke_example.py`
