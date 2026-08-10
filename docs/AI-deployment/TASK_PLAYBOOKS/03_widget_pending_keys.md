# Playbook 03 — Widget pending-key pattern

**Checklist ID:** C3  
**Ask user:** implement yes / no / later?

## Goal

Avoid Streamlit errors when setting a widget’s value after it was instantiated.

## Pattern

```python
def apply_pending(widget_key: str) -> None:
    pending = f"{widget_key}_pending"
    if pending in st.session_state:
        st.session_state[widget_key] = st.session_state.pop(pending)

def queue_value(widget_key: str, value: str) -> None:
    st.session_state[f"{widget_key}_pending"] = value

# BEFORE widget:
apply_pending("my_smiles")
st.text_input("SMILES", key="my_smiles")

# ON BUTTON (after widget already exists this run):
queue_value("my_smiles", new_value)
st.rerun()
```

## When it bites

“Set hit as query”, Sync from editor, Clear, programmatic form fills.
