# Installing Cursor rules from this kit

1. Complete `DEPLOY_CHECKLIST.md` section H.  
2. Copy accepted files into the new project:

```bash
mkdir -p .cursor/rules
cp docs/AI-deployment/CURSOR/rules/architecture.mdc .cursor/rules/
cp docs/AI-deployment/CURSOR/rules/code-complete.mdc .cursor/rules/
cp docs/AI-deployment/CURSOR/rules/oop-streamlit.mdc .cursor/rules/
cp docs/AI-deployment/CURSOR/rules/data-protection.mdc .cursor/rules/
cp docs/AI-deployment/CURSOR/rules/project-decisions.mdc .cursor/rules/
# optional:
# cp .../living-instruction-doc.mdc .cursor/rules/
# cp .../builds-deferred.EXAMPLE.mdc .cursor/rules/builds-deferred.mdc
# cp .../chemistry.EXAMPLE.mdc .cursor/rules/chemistry.mdc   # only if chem
```

3. Edit frontmatter / paths if the kit lives somewhere other than `docs/AI-deployment/`.  
4. Keep rules short; link to playbooks for detail.
