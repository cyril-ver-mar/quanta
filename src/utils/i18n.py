"""L1 — minimal EN/RU strings."""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "Quanta",
        "app_tagline": "Gaussian DFT jobs, archives, and XPS analysis",
        "mode_run": "Run mode (Gaussian available)",
        "mode_analyze": "Analyze mode (import archives / parse logs)",
        "nav_home": "Home",
        "nav_project": "Project",
        "nav_compounds": "Compounds",
        "nav_work_review": "Work review",
        "nav_jobs": "Jobs",
        "nav_queue": "Queue",
        "nav_results": "Results",
        "nav_archive": "Archive",
        "nav_settings": "Settings",
        "soft_cancel": "Request soft cancel",
        "hard_stop": "Hard stop (kill Gaussian)",
        "language": "Language",
        "save": "Save",
        "upload": "Upload",
        "charge": "Charge",
        "multiplicity": "Multiplicity",
        "status": "Status",
        "no_gaussian": "Gaussian executable not found. Queue run is disabled; analysis still works.",
        "review_select": "Select entry",
        "review_style": "Display style",
        "review_atoms": "Coordinates",
        "review_jobs": "Related jobs",
        "review_no_compounds": "Import a compound first (Compounds page).",
        "review_gjf_preview": "Gaussian input preview",
        "workflow_title": "ΔSCF workflow steps",
        "workflow_no_steps": "No workflow steps defined.",
        "workflow_progress": "{done}/{total} steps complete ({pct}%)",
        "workflow_status": "Status",
        "workflow_energy": "SCF energy",
        "workflow_what": "What this step does",
        "workflow_route": "Gaussian route",
        "workflow_create": "Create new workflow",
        "workflow_import_first": "Import a compound first (Compounds page).",
        "workflow_compound": "Compound",
        "workflow_job_name": "Job name (optional)",
        "workflow_job_summary": (
            "This workflow runs **{n_steps} Gaussian jobs**: 1 OPT + 1 neutral SP + "
            "**{n_xps} core-hole SP** (one per C/N/O atom). Functional: **{functional}/{basis}**."
        ),
        "workflow_create_btn": "Create ΔSCF workflow",
        "workflow_created": "Created workflow job #{job_id}. Open Queue to run steps.",
        "workflow_existing": "Existing workflows",
        "workflow_no_jobs": "No jobs yet.",
        "workflow_overview_md": """
Each XPS workflow is a **sequence of Gaussian 09 jobs** for one gas-phase molecule:

| Step | Job type | Purpose |
|------|----------|---------|
| **1** | `OPT` | Relax geometry; write checkpoint |
| **2** | Neutral `SP` | Total energy **E₀**; `pop=full` maps 1s orbitals to atoms |
| **3…N** | Core-hole `SP` | UKS + `Guess=Alter` — remove one 1s electron per C/N/O atom |

**Binding energy:** BE = (E_core-hole − E₀) × 27.211 eV. Optional shift aligns mean C1s to 284.3 eV.

**Before you start:** set charge & multiplicity on Compounds; confirm 3D geometry in Work review; configure PBE/B3LYP in Settings.
""",
        "results_dscf_caption": "ΔSCF binding energies from completed core-hole jobs",
        "results_fixture": "Demo fixture",
        "results_fixture_btn": "Create melanine workflow skeleton (OPT log only)",
        "results_fixture_note": "Job #{job_id} created — complete neutral & core-hole logs on Windows, or import archive.",
        "results_chong_btn": "Import Chong test molecules (ethane + hydrazine)",
        "results_chong_hint": (
            "Small smoke-test structures from Chong 2007 Table 1 (C₂H₆ C1s≈290.7 eV obs; N₂H₄ N1s≈406.1 eV obs). "
            "Import → Jobs → create ΔSCF → Queue. Absolute BEs with PBE/6-31G* will differ from Chong’s PW86-PW91/TZP."
        ),
        "results_chong_ok": "Imported: {names}. Open Jobs to create ΔSCF workflows.",
        "results_recurate": "Re-analyze logs → XPS tables",
        "results_no_summary": "No curated summary yet — finish all workflow steps or click Re-analyze.",
        "results_curated": "Curated {n} ΔSCF peaks",
        "results_core_levels": "Per-atom binding energies",
        "results_spectra": "Simulated spectra (Voigt)",
        "settings_gaussian": "Gaussian / folders",
        "settings_dscf": "ΔSCF XPS",
        "settings_dscf_hint": "PBE matches JPCC-style gas-phase ΔSCF; B3LYP is available for comparison.",
        "settings_c1s_shift": "Shift C1s to reference (284.3 eV)",
        "settings_saved": "Saved to data/settings.json",
        "settings_secrets": "Secrets",
        "settings_secrets_hint": (
            "Optional file `SECRETS` next to `app.py` (copy from `SECRETS.example`). "
            "Transfer the same file to trusted standalone installs. Values are never shown here."
        ),
        "settings_secrets_path": "Path: `{path}`",
        "settings_secrets_found": "Secrets file found. Keys present: {keys}",
        "settings_secrets_missing": "No `SECRETS` file yet — copy `SECRETS.example` → `SECRETS` and add a GitHub token to avoid rate limits.",
        "settings_secrets_token_ok": "GitHub API token: configured ({source}).",
        "settings_secrets_token_env": "from environment",
        "settings_secrets_token_file": "from SECRETS file",
        "settings_secrets_token_missing": "GitHub API token: not set (update checks use 60 requests/hour).",
        "settings_secrets_reload": "Reload secrets file",
        "queue_dscf_caption": "Runs all ready steps of the next queued workflow (OPT → neutral SP → core-hole SPs).",
        "queue_run_next": "Run next workflow",
        "queue_running": "Running Gaussian steps…",
        "queue_live_log": "Live / last step log",
        "update_available": "**{new}** is available (you have {old}).",
        "update_dialog_title": "Update available",
        "update_yes_install": "Upgrade now",
        "update_later": "Later",
        "update_open_release": "Open release on GitHub",
        "update_install_expander": "Download & install update",
        "update_install_help": (
            "Quanta will download the release zip and replace app files. "
            "Your data/, exports/, venv/, and SECRETS are kept. Restart the app afterward."
        ),
        "update_confirm": "I understand app files will be overwritten (data/ and venv/ kept).",
        "update_download_install": "Download & install now",
        "update_working": "Downloading and installing…",
        "update_installed": "Update installed. Please stop and restart the app.",
        "update_restart_hint": "Close the terminal or stop Streamlit, then run again.",
        "update_failed": "Update failed: {err}",
        "update_no_zip": (
            "This release has no downloadable zip — open the release page and download manually."
        ),
        "update_dismiss": "Dismiss",
        "settings_gaussian_cli_hint": (
            "Use the CLI binary (g09.exe or g16.exe), not the Windows GUI (g09w.exe). "
            "The GUI only opens an empty window and will not run jobs from Quanta."
        ),
        "update_section": "Updates",
        "update_not_configured": (
            "GitHub repo not set. Put `owner/name` in the `GITHUB_REPO` file "
            "(or set QUANTA_GITHUB_REPO)."
        ),
        "update_repo": "Repository: `{repo}`",
        "update_local_remote": "Local: **{local}** · Latest on GitHub: **{remote}**",
        "update_up_to_date": "You are on the latest release.",
        "update_check_now": "Check for updates now",
        "update_check_settings_hint": "Open **Settings → Updates** for status and retry.",
        "update_check_detail": "Technical detail: `{detail}`",
        "update_local_only": "Installed version: **{local}** (latest on GitHub unknown).",
        "update_check_network": (
            "Could not connect to GitHub to check for updates. Check internet, proxy, or firewall. ({detail})"
        ),
        "update_check_timeout": (
            "GitHub did not respond in time while checking for updates. Try again later. ({detail})"
        ),
        "update_check_ssl": (
            "Secure connection to GitHub failed (SSL/certificate). A corporate proxy may intercept HTTPS. ({detail})"
        ),
        "update_check_no_releases": (
            "GitHub has no latest release for `{repo}` (repository missing or no releases). ({detail})"
        ),
        "update_check_rate_limit": (
            "GitHub rate limit reached (60 checks/hour without a token). Wait ~15–60 min, "
            "or put `GITHUB_TOKEN=...` in the root `SECRETS` file (see `SECRETS.example`). ({detail})"
        ),
        "update_check_http": "GitHub returned an HTTP error during the update check. ({detail})",
        "update_check_bad_response": (
            "GitHub returned an unexpected response during the update check. ({detail})"
        ),
        "update_check_unexpected": "Update check failed with an unexpected error. ({detail})",
        "project_page_caption": "Group compounds and ΔSCF jobs in one reloadable workspace (like XPS-Deconv projects).",
        "project_section": "Project",
        "new_project_name": "New project name",
        "create_project": "Create project",
        "created_project": "Created project «{name}».",
        "load_existing": "Load existing",
        "project_list_item": "{name} ({n} compounds) — {updated}",
        "load_project": "Load project",
        "delete_project": "Delete project",
        "deleted_ok": "Project deleted.",
        "no_projects": "No projects yet — create one on the left.",
        "need_project": "Create or load a project on the **Project** page first.",
        "active_project": "Active: **{name}** · `{id}` · {n} compound(s)",
        "project_notes": "Project notes",
        "save_notes": "Save notes",
        "saved_ok": "Saved.",
        "project_add_compounds": "Add compounds to this project",
        "project_import_btn": "Import into project",
        "project_added_compounds": "Added {n} compound(s) to the project.",
        "project_entries": "Entries in this project",
        "project_no_entries": "No compounds in this project yet — upload above or use the Compounds page.",
        "project_entry_id": "Entry `{id}` → compound #{compound_id}",
        "project_set_active": "Set as active compound",
        "project_remove_entry": "Remove from project",
        "project_active_entry": "Active compound: **{label}** (`{id}`)",
        "project_n_compounds": "Compounds in project",
        "project_n_jobs": "Jobs in project",
        "soft_cancel_ok": "Soft cancel requested",
        "hard_stop_ok": "Hard stop requested",
        "project_loaded": "Project loaded.",
        "project_default_name": "My ΔSCF project",
        "project_entry_jobs": "{label} ({formula}) · {n} job(s)",
        "compound_name": "Name",
        "import_btn": "Import",
        "compound_imported": "Imported compound id={id}",
        "compound_library": "Library",
        "compound_empty": "No compounds yet.",
        "compound_goto_review": "3D review →",
        "atoms": "Atoms",
        "formula": "Formula",
        "field_format": "Format",
        "path_label": "Path",
        "meta_label": "Meta",
        "review_caption": "Inspect 3D geometry, charge/multiplicity, and linked jobs before queuing Gaussian.",
        "review_style_ballstick": "ball+stick",
        "review_elements": "Elements: {list}",
        "review_3d": "3D model",
        "review_no_jobs": "No jobs yet for this compound. Create one on the Jobs page.",
        "review_create_job": "Create job for this compound",
        "review_job_queued": "Queued job id={id}",
        "workflow_route_caption": "Step 1 route: `{route}` · nproc={nproc} · mem={mem} MB",
        "workflow_io_caption": "Input: `{gjf}` · Log: `{log}`",
        "workflow_alter_caption": "Alter swap: orbital {orbital} (1s) ↔ {homo} (HOMO)",
        "step_opt_title": "Step 1 · Geometry optimization",
        "step_opt_hint": (
            "Optimizes 3D geometry in the gas phase. "
            "Uses your charge and multiplicity from Compounds. "
            "Produces a checkpoint for all later single-points."
        ),
        "step_neutral_title": "Step 2 · Neutral ground-state SP",
        "step_neutral_hint": (
            "Single-point at the OPT geometry with pop=full. "
            "Records E₀ and maps each atom's 1s orbital for core-hole jobs. "
            "Requires Step 1 checkpoint."
        ),
        "step_corehole_title": "Step {n} · Core hole on {label}",
        "step_corehole_hint": (
            "UKS single-point with a 1s core hole on atom {atom} ({element}). "
            "Guess=Alter swaps that atom's 1s with HOMO (doublet). "
            "BE = E(core hole) − E₀. Requires Step 2."
        ),
        "queue_pause": "Pause remaining queue",
        "queue_resume": "Resume paused",
        "queue_finished": "Finished processing job {job_id}",
        "queue_nothing": "No queued job or Gaussian unavailable",
        "queue_delete_pending": "Delete pending",
        "queue_deleted": "Deleted",
        "queue_restart": "Re-queue / restart",
        "queue_requeued": "Re-queued",
        "queue_refresh": "Refresh monitor",
        "job_id": "Job id",
        "col_id": "id",
        "col_name": "name",
        "col_status": "status",
        "col_progress": "progress",
        "col_route": "route",
        "col_current_step": "current_step",
        "col_eta": "eta_s",
        "col_error": "error",
        "monitor_opt_steps": "opt_steps",
        "monitor_progress": "progress",
        "monitor_scf_points": "scf_points",
        "monitor_normal_term": "normal_termination",
        "results_job_select": "Job",
        "results_e0": "E₀ (Ha)",
        "results_homo": "HOMO (eV)",
        "results_lumo": "LUMO (eV)",
        "results_gap": "Gap (eV)",
        "results_n_corehole": "Core-hole jobs",
        "results_dl_core_csv": "core_levels.csv",
        "results_spectrum_title": "{element}1s (ΔSCF + Voigt)",
        "results_be_axis": "Binding energy (eV)",
        "results_intensity_axis": "Intensity (a.u.)",
        "archive_help_md": """
Export a zip on the **Windows** machine after calculations, copy it here, then **Import** on **Mac**
to analyze without Gaussian.
""",
        "archive_jobs_select": "Jobs to export (empty = all on disk)",
        "archive_export": "Export zip",
        "archive_wrote": "Wrote {path}",
        "archive_download": "Download archive",
        "archive_upload": "Import archive zip",
        "archive_imported": "Imported jobs: {imported}",
        "settings_gaussian_exe": "Gaussian executable path",
        "settings_work_dir": "Work directory (optional)",
        "settings_work_dir_hint": "Gaussian files go under: work_dir / project_name / job_id_description /",
        "settings_scratch_dir": "Scratch / GAUSS_SCRDIR (optional)",
        "settings_nproc": "%nprocshared",
        "settings_mem": "%mem MB",
        "settings_functional": "Functional",
        "settings_basis": "Basis set",
        "settings_fwhm": "Voigt FWHM (eV)",
        "settings_c1s_ref": "C1s reference (eV)",
        "home_workflow_md": """
### Workflow (ΔSCF XPS)
0. **Project** — create/load a workspace; compounds & jobs belong to one project  
1. **Settings** — Gaussian path, PBE/B3LYP, Voigt FWHM, C1s reference  
2. **Compounds** — upload mol2 / pdb / sdf (RDKit) into the active project  
3. **Work review** — 3D structure preview before calculations  
4. **Jobs** — create a multi-step ΔSCF workflow (see step guide)  
5. **Queue** — run steps one-by-one on Windows (disabled on Mac without `g09`)  
6. **Results** — ΔSCF binding energies and C/N/O spectra  
7. **Archive** — export zip on Windows → import on Mac for analysis  

**Method:** gas-phase ΔSCF in Gaussian 09 — OPT → neutral SP (E₀) → core-hole SP per atom (BE = ΔE).
""",
        "update_repo_file_exists": "`{path}` — exists: **{exists}**",
        "update_repo_parse_fail": (
            "GITHUB_REPO was found but no valid `owner/name` line was parsed. "
            "Use one line like `cyril-ver-mar/quanta` (comments with `#` are OK on other lines)."
        ),
        "update_repo_create_hint": (
            "Create `{name}` in the app folder (next to `app.py`) "
            "with one line: `cyril-ver-mar/quanta`"
        ),
    },
    "ru": {
        "app_title": "Quanta",
        "app_tagline": "Задачи Gaussian DFT, архивы и анализ XPS",
        "mode_run": "Режим расчёта (Gaussian доступен)",
        "mode_analyze": "Режим анализа (импорт архивов / разбор логов)",
        "nav_home": "Главная",
        "nav_project": "Проект",
        "nav_compounds": "Соединения",
        "nav_work_review": "Обзор структуры",
        "nav_jobs": "Задачи",
        "nav_queue": "Очередь",
        "nav_results": "Результаты",
        "nav_archive": "Архив",
        "nav_settings": "Настройки",
        "soft_cancel": "Мягкая отмена",
        "hard_stop": "Жёсткая остановка (убить Gaussian)",
        "language": "Язык",
        "save": "Сохранить",
        "upload": "Загрузить",
        "charge": "Заряд",
        "multiplicity": "Мультиплетность",
        "status": "Статус",
        "no_gaussian": "Исполняемый файл Gaussian не найден. Запуск очереди отключён; анализ доступен.",
        "review_select": "Выберите запись",
        "review_style": "Стиль отображения",
        "review_atoms": "Координаты",
        "review_jobs": "Связанные задачи",
        "review_no_compounds": "Сначала импортируйте соединение (страница Соединения).",
        "review_gjf_preview": "Предпросмотр входного файла Gaussian",
        "workflow_title": "Шаги ΔSCF",
        "workflow_no_steps": "Шаги не заданы.",
        "workflow_progress": "{done}/{total} шагов ({pct}%)",
        "workflow_status": "Статус",
        "workflow_energy": "Энергия SCF",
        "workflow_what": "Назначение шага",
        "workflow_route": "Маршрут Gaussian",
        "workflow_create": "Создать workflow",
        "workflow_import_first": "Сначала импортируйте соединение.",
        "workflow_compound": "Соединение",
        "workflow_job_name": "Имя задачи (необяз.)",
        "workflow_job_summary": (
            "Будет **{n_steps} расчётов**: 1 OPT + 1 нейтральный SP + **{n_xps} core-hole SP** "
            "(по одному на каждый C/N/O). Functional: **{functional}/{basis}**."
        ),
        "workflow_create_btn": "Создать ΔSCF workflow",
        "workflow_created": "Создана задача #{job_id}. Запуск — на странице Очередь.",
        "workflow_existing": "Существующие workflow",
        "workflow_no_jobs": "Задач пока нет.",
        "workflow_overview_md": """
Workflow XPS — **цепочка задач Gaussian 09** для молекулы в газовой фазе:

| Шаг | Тип | Цель |
|-----|-----|------|
| **1** | `OPT` | Оптимизация геометрии; checkpoint |
| **2** | Нейтральный `SP` | Энергия **E₀**; `pop=full` — номера 1s орбиталей |
| **3…N** | Core-hole `SP` | UKS + `Guess=Alter` — дырка в 1s для каждого C/N/O |

**BE** = (E_core-hole − E₀) × 27.211 eV. Опционально — сдвиг C1s к 284.3 eV.

**Перед стартом:** заряд и мультиплетность на странице Соединения; 3D в Обзоре; PBE/B3LYP в Настройках.
""",
        "results_dscf_caption": "BE из ΔSCF (завершённые core-hole расчёты)",
        "results_fixture": "Демо",
        "results_fixture_btn": "Создать skeleton melanine (только OPT log)",
        "results_fixture_note": "Задача #{job_id} — завершите neutral/core-hole на Windows или импортируйте архив.",
        "results_chong_btn": "Импорт тест-молекул Chong (этан + гидразин)",
        "results_chong_hint": (
            "Малые молекулы из Chong 2007, табл. 1 (C₂H₆ C1s≈290.7 эВ; N₂H₄ N1s≈406.1 эВ). "
            "Импорт → Jobs → ΔSCF → Очередь. Абсолютные BE при PBE/6-31G* не совпадут с методом Chong."
        ),
        "results_chong_ok": "Импортировано: {names}. Создайте ΔSCF на странице Jobs.",
        "results_recurate": "Пересобрать таблицы XPS",
        "results_no_summary": "Нет summary — завершите workflow или нажмите Пересобрать.",
        "results_curated": "Собрано пиков ΔSCF: {n}",
        "results_core_levels": "BE по атомам",
        "results_spectra": "Симулированные спектры (Voigt)",
        "settings_gaussian": "Gaussian / каталоги",
        "settings_dscf": "ΔSCF XPS",
        "settings_dscf_hint": "PBE ближе к gas-phase ΔSCF из JPCC; B3LYP — для сравнения.",
        "settings_c1s_shift": "Сдвиг C1s к 284.3 eV",
        "settings_saved": "Сохранено в data/settings.json",
        "settings_secrets": "Секреты",
        "settings_secrets_hint": (
            "Необязательный файл `SECRETS` рядом с `app.py` (скопируйте из `SECRETS.example`). "
            "Можно переносить в доверенные standalone-установки. Значения здесь не показываются."
        ),
        "settings_secrets_path": "Путь: `{path}`",
        "settings_secrets_found": "Файл секретов найден. Ключи: {keys}",
        "settings_secrets_missing": "Нет файла `SECRETS` — скопируйте `SECRETS.example` → `SECRETS` и укажите токен GitHub.",
        "settings_secrets_token_ok": "Токен GitHub API: задан ({source}).",
        "settings_secrets_token_env": "из переменной окружения",
        "settings_secrets_token_file": "из файла SECRETS",
        "settings_secrets_token_missing": "Токен GitHub API: не задан (лимит обновлений 60 запросов/час).",
        "settings_secrets_reload": "Перечитать файл секретов",
        "queue_dscf_caption": "Запуск готовых шагов следующего workflow (OPT → neutral SP → core-hole SP).",
        "queue_run_next": "Запустить workflow",
        "queue_running": "Идёт расчёт Gaussian…",
        "queue_live_log": "Текущий / последний log",
        "update_available": "Доступна версия **{new}** (у вас {old}).",
        "update_dialog_title": "Доступно обновление",
        "update_yes_install": "Обновить сейчас",
        "update_later": "Позже",
        "update_open_release": "Открыть релиз на GitHub",
        "update_install_expander": "Скачать и установить обновление",
        "update_install_help": (
            "Quanta скачает zip релиза и заменит файлы приложения. "
            "Каталоги data/, exports/, venv/ и файл SECRETS сохраняются. Затем перезапустите приложение."
        ),
        "update_confirm": "Понимаю: файлы приложения будут перезаписаны (data/ и venv/ сохранятся).",
        "update_download_install": "Скачать и установить сейчас",
        "update_working": "Скачивание и установка…",
        "update_installed": "Обновление установлено. Остановите и перезапустите приложение.",
        "update_restart_hint": "Закройте терминал или остановите Streamlit, затем запустите снова.",
        "update_failed": "Ошибка обновления: {err}",
        "update_no_zip": (
            "У этого релиза нет скачиваемого zip — откройте страницу релиза и скачайте вручную."
        ),
        "update_dismiss": "Скрыть",
        "settings_gaussian_cli_hint": (
            "Укажите CLI-файл (g09.exe или g16.exe), а не Windows GUI (g09w.exe). "
            "GUI только открывает пустое окно и не запускает задания из Quanta."
        ),
        "update_section": "Обновления",
        "update_not_configured": (
            "Репозиторий GitHub не задан. Укажите `owner/name` в файле `GITHUB_REPO` "
            "(или переменной QUANTA_GITHUB_REPO)."
        ),
        "update_repo": "Репозиторий: `{repo}`",
        "update_local_remote": "Локально: **{local}** · На GitHub: **{remote}**",
        "update_up_to_date": "У вас последняя версия.",
        "update_check_now": "Проверить обновления сейчас",
        "update_check_settings_hint": "Откройте **Настройки → Обновления**, чтобы увидеть статус и повторить проверку.",
        "update_check_detail": "Техническая деталь: `{detail}`",
        "update_local_only": "Установленная версия: **{local}** (последняя на GitHub неизвестна).",
        "update_check_network": (
            "Не удалось подключиться к GitHub для проверки обновлений. Проверьте интернет, прокси или брандмауэр. ({detail})"
        ),
        "update_check_timeout": (
            "GitHub не ответил вовремя при проверке обновлений. Попробуйте позже. ({detail})"
        ),
        "update_check_ssl": (
            "Не удалось установить защищённое соединение с GitHub (SSL/сертификат). Корпоративный прокси может перехватывать HTTPS. ({detail})"
        ),
        "update_check_no_releases": (
            "На GitHub нет последнего релиза для `{repo}` (репозиторий не найден или нет релизов). ({detail})"
        ),
        "update_check_rate_limit": (
            "Лимит запросов GitHub (60/час без токена). Подождите ~15–60 мин или укажите "
            "`GITHUB_TOKEN=...` в файле `SECRETS` (см. `SECRETS.example`). ({detail})"
        ),
        "update_check_http": "GitHub вернул HTTP-ошибку при проверке обновлений. ({detail})",
        "update_check_bad_response": (
            "GitHub вернул неожиданный ответ при проверке обновлений. ({detail})"
        ),
        "update_check_unexpected": "Проверка обновлений завершилась неожиданной ошибкой. ({detail})",
        "project_page_caption": "Группируйте соединения и задачи ΔSCF в одном перезагружаемом проекте (как в XPS-Deconv).",
        "project_section": "Проект",
        "new_project_name": "Имя нового проекта",
        "create_project": "Создать проект",
        "created_project": "Создан проект «{name}».",
        "load_existing": "Загрузить существующий",
        "project_list_item": "{name} ({n} соединений) — {updated}",
        "load_project": "Загрузить проект",
        "delete_project": "Удалить проект",
        "deleted_ok": "Проект удалён.",
        "no_projects": "Проектов пока нет — создайте слева.",
        "need_project": "Сначала создайте или загрузите проект на странице **Проект**.",
        "active_project": "Активный: **{name}** · `{id}` · {n} соедин.",
        "project_notes": "Заметки к проекту",
        "save_notes": "Сохранить заметки",
        "saved_ok": "Сохранено.",
        "project_add_compounds": "Добавить соединения в проект",
        "project_import_btn": "Импорт в проект",
        "project_added_compounds": "Добавлено соединений: {n}.",
        "project_entries": "Записи проекта",
        "project_no_entries": "В проекте пока нет соединений — загрузите выше или на странице Соединения.",
        "project_entry_id": "Запись `{id}` → соединение #{compound_id}",
        "project_set_active": "Сделать активным",
        "project_remove_entry": "Убрать из проекта",
        "project_active_entry": "Активное соединение: **{label}** (`{id}`)",
        "project_n_compounds": "Соединений в проекте",
        "project_n_jobs": "Задач в проекте",
        "soft_cancel_ok": "Мягкая отмена запрошена",
        "hard_stop_ok": "Жёсткая остановка запрошена",
        "project_loaded": "Проект загружен.",
        "project_default_name": "Мой проект ΔSCF",
        "project_entry_jobs": "{label} ({formula}) · {n} задач(и)",
        "compound_name": "Имя",
        "import_btn": "Импорт",
        "compound_imported": "Импортировано соединение id={id}",
        "compound_library": "Библиотека",
        "compound_empty": "Соединений пока нет.",
        "compound_goto_review": "3D обзор →",
        "atoms": "Атомы",
        "formula": "Формула",
        "field_format": "Формат",
        "path_label": "Путь",
        "meta_label": "Мета",
        "review_caption": "Проверьте 3D-геометрию, заряд/мультиплетность и связанные задачи перед постановкой в очередь Gaussian.",
        "review_style_ballstick": "шарики+стержни",
        "review_elements": "Элементы: {list}",
        "review_3d": "3D-модель",
        "review_no_jobs": "Для этого соединения ещё нет задач. Создайте на странице Jobs.",
        "review_create_job": "Создать задачу для этого соединения",
        "review_job_queued": "В очередь поставлена задача id={id}",
        "workflow_route_caption": "Маршрут шага 1: `{route}` · nproc={nproc} · mem={mem} MB",
        "workflow_io_caption": "Вход: `{gjf}` · Log: `{log}`",
        "workflow_alter_caption": "Alter: орбиталь {orbital} (1s) ↔ {homo} (HOMO)",
        "step_opt_title": "Шаг 1 · Оптимизация геометрии",
        "step_opt_hint": (
            "Оптимизирует 3D-геометрию в газовой фазе. "
            "Использует заряд и мультиплетность со страницы Соединения. "
            "Создаёт checkpoint для последующих single-point."
        ),
        "step_neutral_title": "Шаг 2 · Нейтральный SP основного состояния",
        "step_neutral_hint": (
            "Single-point на геометрии OPT с pop=full. "
            "Записывает E₀ и сопоставляет 1s-орбитали атомам для core-hole. "
            "Нужен checkpoint шага 1."
        ),
        "step_corehole_title": "Шаг {n} · Core hole на {label}",
        "step_corehole_hint": (
            "UKS single-point с дыркой в 1s на атоме {atom} ({element}). "
            "Guess=Alter меняет 1s этого атома с HOMO (дублет). "
            "BE = E(core hole) − E₀. Нужен шаг 2."
        ),
        "queue_pause": "Приостановить очередь",
        "queue_resume": "Возобновить паузу",
        "queue_finished": "Обработка задачи {job_id} завершена",
        "queue_nothing": "Нет задачи в очереди или Gaussian недоступен",
        "queue_delete_pending": "Удалить ожидающую",
        "queue_deleted": "Удалено",
        "queue_restart": "Снова в очередь / перезапуск",
        "queue_requeued": "Снова в очереди",
        "queue_refresh": "Обновить монитор",
        "job_id": "ID задачи",
        "col_id": "id",
        "col_name": "имя",
        "col_status": "статус",
        "col_progress": "прогресс",
        "col_route": "маршрут",
        "col_current_step": "текущий_шаг",
        "col_eta": "eta_с",
        "col_error": "ошибка",
        "monitor_opt_steps": "шаги_opt",
        "monitor_progress": "прогресс",
        "monitor_scf_points": "точки_scf",
        "monitor_normal_term": "нормальное_завершение",
        "results_job_select": "Задача",
        "results_e0": "E₀ (Ha)",
        "results_homo": "HOMO (эВ)",
        "results_lumo": "LUMO (эВ)",
        "results_gap": "Щель (эВ)",
        "results_n_corehole": "Core-hole задачи",
        "results_dl_core_csv": "core_levels.csv",
        "results_spectrum_title": "{element}1s (ΔSCF + Voigt)",
        "results_be_axis": "Энергия связи (эВ)",
        "results_intensity_axis": "Интенсивность (отн. ед.)",
        "archive_help_md": """
Экспортируйте zip на машине **Windows** после расчётов, скопируйте сюда и **импортируйте** на **Mac**,
чтобы анализировать без Gaussian.
""",
        "archive_jobs_select": "Задачи для экспорта (пусто = все на диске)",
        "archive_export": "Экспорт zip",
        "archive_wrote": "Записано: {path}",
        "archive_download": "Скачать архив",
        "archive_upload": "Импорт архива zip",
        "archive_imported": "Импортированы задачи: {imported}",
        "settings_gaussian_exe": "Путь к исполняемому файлу Gaussian",
        "settings_work_dir": "Рабочий каталог (необяз.)",
        "settings_work_dir_hint": "Файлы Gaussian: work_dir / имя_проекта / id_описание_задания /",
        "settings_scratch_dir": "Scratch / GAUSS_SCRDIR (необяз.)",
        "settings_nproc": "%nprocshared",
        "settings_mem": "%mem MB",
        "settings_functional": "Функционал",
        "settings_basis": "Базисный набор",
        "settings_fwhm": "Voigt FWHM (эВ)",
        "settings_c1s_ref": "Референс C1s (эВ)",
        "home_workflow_md": """
### Workflow (ΔSCF XPS)
0. **Проект** — создать/загрузить рабочее пространство; соединения и задачи принадлежат одному проекту  
1. **Настройки** — путь Gaussian, PBE/B3LYP, Voigt FWHM, референс C1s  
2. **Соединения** — загрузка mol2 / pdb / sdf (RDKit) в активный проект  
3. **Обзор структуры** — 3D-просмотр перед расчётами  
4. **Задачи** — создать многошаговый ΔSCF workflow (см. описание шагов)  
5. **Очередь** — запуск шагов по одному на Windows (на Mac без `g09` отключён)  
6. **Результаты** — энергии связи ΔSCF и спектры C/N/O  
7. **Архив** — экспорт zip на Windows → импорт на Mac для анализа  

**Метод:** gas-phase ΔSCF в Gaussian 09 — OPT → нейтральный SP (E₀) → core-hole SP на атом (BE = ΔE).
""",
        "update_repo_file_exists": "`{path}` — существует: **{exists}**",
        "update_repo_parse_fail": (
            "Файл GITHUB_REPO найден, но строка `owner/name` не разобрана. "
            "Укажите одну строку вида `cyril-ver-mar/quanta` (комментарии с `#` на других строках допустимы)."
        ),
        "update_repo_create_hint": (
            "Создайте `{name}` в папке приложения (рядом с `app.py`) "
            "с одной строкой: `cyril-ver-mar/quanta`"
        ),
    },
}


def t(key: str, lang: str = "en", **fmt) -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    text = table.get(key) or STRINGS["en"].get(key, key)
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, ValueError):
            return text
    return text
