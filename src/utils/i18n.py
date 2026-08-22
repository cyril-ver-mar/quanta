"""L1 — minimal EN/RU strings."""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "Quanta",
        "app_tagline": "Gaussian DFT jobs, archives, and XPS analysis",
        "mode_run": "Run mode (Gaussian available)",
        "mode_analyze": "Analyze mode (import archives / parse logs)",
        "nav_home": "Home",
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
        "queue_dscf_caption": "Runs all ready steps of the next queued workflow (OPT → neutral SP → core-hole SPs).",
        "queue_run_next": "Run next workflow",
        "queue_running": "Running Gaussian steps…",
        "queue_live_log": "Live / last step log",
    },
    "ru": {
        "app_title": "Quanta",
        "app_tagline": "Задачи Gaussian DFT, архивы и анализ XPS",
        "mode_run": "Режим расчёта (Gaussian доступен)",
        "mode_analyze": "Режим анализа (импорт архивов / разбор логов)",
        "nav_home": "Главная",
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
        "queue_dscf_caption": "Запуск готовых шагов следующего workflow (OPT → neutral SP → core-hole SP).",
        "queue_run_next": "Запустить workflow",
        "queue_running": "Идёт расчёт Gaussian…",
        "queue_live_log": "Текущий / последний log",
    },
}


def t(key: str, lang: str = "en") -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    return table.get(key) or STRINGS["en"].get(key, key)
