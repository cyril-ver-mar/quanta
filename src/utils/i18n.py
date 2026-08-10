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
    },
    "ru": {
        "app_title": "Quanta",
        "app_tagline": "Задачи Gaussian DFT, архивы и анализ XPS",
        "mode_run": "Режим расчёта (Gaussian доступен)",
        "mode_analyze": "Режим анализа (импорт архивов / разбор логов)",
        "nav_home": "Главная",
        "nav_compounds": "Соединения",
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
    },
}


def t(key: str, lang: str = "en") -> str:
    table = STRINGS.get(lang) or STRINGS["en"]
    return table.get(key) or STRINGS["en"].get(key, key)
