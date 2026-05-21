"""Сервис документов.

Пока нет PostgreSQL, документы берутся из data/documents.json.
Позже этот слой будет заменён на запросы к PostgreSQL.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.categories import CATEGORY_BY_SLUG, CATEGORIES

DATA_FILE = Path("data/documents.json")

CATEGORY_TITLES = {
    "state-ai-strategy": "Государственная стратегия развития ИИ",
    "digital-policy": "Цифровая политика государства",
    "ai-legal-concept": "Концепция правового регулирования ИИ",
    "soft-law": "Мягкое регулирование",

    "base-laws": "Базовые законы для ИИ",
    "experimental-regulation": "Экспериментальное регулирование",
    "legislative-initiatives": "Законодательные инициативы",

    "standardization": "Стандартизация",
    "base-ai-gost": "Базовые ГОСТы по ИИ",
    "data-gost": "ГОСТы по данным",
    "industry-gost": "Отраслевые ГОСТы",
    "trust-security-gost": "ГОСТы по безопасности и доверию",

    "it": "IT и цифровая экономика",
    "transport": "Транспорт и БПЛА",
    "agriculture": "Сельское хозяйство и АПК",

    "legislation": "Нормативные акты",
    "strategy": "Стратегический уровень",
    "support": "Государственная поддержка и внедрение",
    "financial-support": "Финансовая поддержка",
    "research-support": "Исследовательская поддержка",
    "ai-project-criteria": "Критерии ИИ-проектов",

    "it-gost": "IT / ИИ",
    "transport-gost": "Транспорт и БПЛА",
    "agriculture-gost": "Сельское хозяйство",
}

CATEGORY_SLUG_ALIASES = {
    # старые кривые значения
    "standardization_it": "it-gost",
    "standardization-it": "it-gost",
    "transport_legislation": "transport",
    "transport legislation": "transport",
    "agro": "agriculture",
    "apk": "agriculture",

    # русские названия, которые могли уже попасть в documents.json
    "Государственная стратегия развития ИИ": "state-ai-strategy",
    "Цифровая политика государства": "digital-policy",
    "Концепция правового регулирования ИИ": "ai-legal-concept",
    "Мягкое регулирование": "soft-law",

    "Базовые законы для ИИ": "base-laws",
    "Экспериментальное регулирование": "experimental-regulation",
    "Законодательные инициативы": "legislative-initiatives",

    "Стандартизация": "standardization",
    "Базовые ГОСТы по ИИ": "base-ai-gost",
    "ГОСТы по данным": "data-gost",
    "Отраслевые ГОСТы": "industry-gost",

    "IT и цифровая экономика": "it",
    "Транспорт и БПЛА": "transport",
    "Транспорт и беспилотные системы": "transport",
    "Сельское хозяйство и АПК": "agriculture",
    "Сельское хозяйство": "agriculture",
}


def normalize_category_slug(value: str | None) -> str:
    """
    Приводит категорию к внутреннему slug.

    Пример:
    'Сельское хозяйство и АПК' -> 'agriculture'
    'agriculture' -> 'agriculture'
    """
    if not value:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    if value in CATEGORY_BY_SLUG:
        return value

    if value in CATEGORY_SLUG_ALIASES:
        return CATEGORY_SLUG_ALIASES[value]

    lower_value = value.lower()

    for title, slug in CATEGORY_SLUG_ALIASES.items():
        if title.lower() == lower_value:
            return slug

    return value


def normalize_category_slugs(raw_categories: list[str] | None) -> list[str]:
    """
    Приводит список категорий к slug из app/core/categories.py.
    """
    result: list[str] = []

    for raw in raw_categories or []:
        value = str(raw).strip()

        if not value:
            continue

        # Если случайно сохранили строку с несколькими slug через пробел:
        # "transport legislation"
        parts = value.split() if " " in value and value not in CATEGORY_BY_SLUG and value not in CATEGORY_SLUG_ALIASES else [value]

        for part in parts:
            slug = normalize_category_slug(part)

            if slug and slug not in result:
                result.append(slug)

    return result

def _read_json_documents() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text("[]", encoding="utf-8")
        return []

    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _write_json_documents(documents: list[dict[str, Any]]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(documents, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_demo_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Приводим старые demo-документы к новой схеме с categories."""
    doc = dict(doc)
    doc.setdefault("source_name", "Демо-данные")
    doc.setdefault("source_url", "")
    doc.setdefault("is_parsed", False)
    doc.setdefault("downloaded", False)
    doc.setdefault("categories", [])

    old_category = (doc.get("category") or "").lower()
    doc["categories"] = normalize_category_slugs(doc.get("categories"))

    if not doc["categories"]:
        if "стандарт" in old_category or doc.get("type") in {"ГОСТ Р", "ПНСТ"}:
            doc["categories"] = ["standardization"]
        elif "сель" in old_category or "апк" in old_category:
            doc["categories"] = ["agriculture"]
        elif "эксперимент" in old_category:
            doc["categories"] = ["experimental-regulation"]
        elif "закон" in old_category:
            doc["categories"] = ["legislation"]
        elif "стратег" in old_category:
            doc["categories"] = ["strategy"]
        else:
            doc["categories"] = ["it"]
    return doc


def normalize_json_document(doc: dict[str, Any]) -> dict[str, Any]:
    """Нормализует документы из data/documents.json перед выводом на сайте."""
    doc = dict(doc)
    doc.setdefault("source_name", "JSON-хранилище")
    doc.setdefault("source_url", "")
    doc.setdefault("is_parsed", True)
    doc.setdefault("downloaded", False)

    raw_categories = doc.get("categories") or []

    if doc.get("category"):
        raw_categories.append(doc.get("category"))

    doc["categories"] = normalize_category_slugs(raw_categories) or ["it"]

    return doc


def get_all_documents() -> list[dict]:
    """
    Возвращает документы из data/documents.json.
    Старые demo-документы больше не подмешиваются в каталог.
    """
    docs = [
        normalize_json_document(doc)
        for doc in _read_json_documents()
    ]

    return sorted(
        docs,
        key=lambda item: str(
            item.get("published_at")
            or item.get("date")
            or item.get("adopted_at")
            or item.get("id")
            or ""
        ),
        reverse=True,
    )

def get_document(document_id: str | int) -> dict[str, Any] | None:
    """
    Возвращает документ по id.

    id может быть:
    - числом, например 1;
    - строкой, например official-http-publication...
    """
    document_id_str = str(document_id)

    return next(
        (
            doc
            for doc in get_all_documents()
            if str(doc.get("id", "")) == document_id_str
        ),
        None,
    )

def filter_documents(
    query: str = "",
    category: str = "",
    doc_type: str = "",
    status: str = "",
) -> list[dict]:
    """
    Фильтрует документы для каталога.
    Категории сравниваются по slug, даже если в JSON случайно лежит русское название.
    """

    documents = get_all_documents()

    query = (query or "").strip().lower()
    selected_category = normalize_category_slug(category)
    doc_type = (doc_type or "").strip()
    status = (status or "").strip()

    result = []

    for doc in documents:
        title = str(doc.get("title", "")).lower()
        short_title = str(doc.get("short_title", "")).lower()
        number = str(doc.get("number", "")).lower()
        summary = str(doc.get("summary", "")).lower()
        authority = str(doc.get("authority", "")).lower()

        raw_categories = doc.get("categories") or []

        if doc.get("category"):
            raw_categories.append(doc.get("category"))

        doc_categories = normalize_category_slugs(raw_categories)

        doc_type_value = str(doc.get("doc_type") or doc.get("type") or "")
        status_value = str(doc.get("status") or "")

        if query:
            search_text = " ".join(
                [title, short_title, number, summary, authority]
            )

            if query not in search_text:
                continue

        if selected_category:
            if selected_category not in doc_categories:
                continue

        if doc_type:
            if doc_type.lower() != doc_type_value.lower():
                continue

        if status:
            if status.lower() != status_value.lower():
                continue

        result.append(doc)

    return result

def get_documents_by_category(category_slug: str) -> list[dict[str, Any]]:
    return filter_documents(category=category_slug)


def get_category_title(slug: str) -> str:
    normalized_slug = normalize_category_slug(slug)

    if normalized_slug in CATEGORY_BY_SLUG:
        return CATEGORY_BY_SLUG[normalized_slug].get("title", normalized_slug)

    return CATEGORY_TITLES.get(normalized_slug, normalized_slug)


def get_next_id() -> str:
    existing_ids = [str(doc.get("id", 0)) for doc in get_all_documents()]
    return max(existing_ids, default=0) + 1


def document_exists(source_url: str = "", number: str = "", title: str = "") -> bool:
    docs = get_all_documents()
    for doc in docs:
        if source_url and doc.get("source_url") == source_url:
            return True
        if number and title and doc.get("number") == number and doc.get("title") == title:
            return True
    return False


def add_parsed_documents(new_documents: list[dict]) -> int:
    """
    Добавляет новые документы в data/documents.json.
    Дубли проверяются по id и source_url.
    Возвращает количество реально добавленных документов.
    """
    documents = _read_json_documents()

    existing_ids = {
        str(doc.get("id"))
        for doc in documents
        if doc.get("id")
    }

    existing_urls = {
        str(doc.get("source_url"))
        for doc in documents
        if doc.get("source_url")
    }

    added = 0

    for doc in new_documents:
        doc_id = str(doc.get("id", ""))
        source_url = str(doc.get("source_url", ""))

        if doc_id and doc_id in existing_ids:
            continue

        if source_url and source_url in existing_urls:
            continue

        documents.append(doc)

        if doc_id:
            existing_ids.add(doc_id)

        if source_url:
            existing_urls.add(source_url)

        added += 1

    _write_json_documents(documents)
    return added


def get_category_options() -> list[dict[str, str]]:
    return CATEGORIES

def get_doc_type_options() -> list[str]:
    """
    Возвращает список типов документов из реальных документов.
    Например: Федеральный закон, ГОСТ Р, Приказ, Распоряжение.
    """
    values = set()

    for doc in get_all_documents():
        value = str(doc.get("doc_type") or doc.get("type") or "").strip()
        if value:
            values.add(value)

    return sorted(values)


def get_status_options() -> list[str]:
    """
    Возвращает список статусов из реальных документов.
    """
    values = set()

    for doc in get_all_documents():
        value = str(doc.get("status") or "").strip()
        if value:
            values.add(value)

    return sorted(values)