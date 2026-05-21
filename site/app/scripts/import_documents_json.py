import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.categories import CATEGORY_BY_SLUG
from app.database import SessionLocal, init_db
from app.models import Category, Document


DATA_FILE = Path("data/documents.json")


CATEGORY_ALIASES = {
    "Сельское хозяйство и АПК": "agriculture",
    "Сельское хозяйство": "agriculture",
    "Транспорт и БПЛА": "transport",
    "Транспорт и беспилотные системы": "transport",
    "IT и цифровая экономика": "it",
    "Стандартизация": "standardization",
    "Базовые ГОСТы по ИИ": "base-ai-gost",
    "Отраслевые ГОСТы": "industry-gost",
    "ГОСТы по данным": "data-gost",
    "Экспериментальное регулирование": "experimental-regulation",
    "Базовые законы для ИИ": "base-laws",
    "Государственная стратегия развития ИИ": "state-ai-strategy",
    "Концепция правового регулирования ИИ": "ai-legal-concept",
}


def clean(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def make_id_from_url(source_url: str) -> str:
    value = source_url.replace("https://", "").replace("http://", "")
    value = re.sub(r"[^a-zA-Z0-9а-яА-Я]+", "-", value)
    value = value.strip("-").lower()
    return value[:180] or "document-without-id"


def normalize_category_slug(value: Any) -> str:
    value = clean(value)

    if not value:
        return ""

    if value in CATEGORY_BY_SLUG:
        return value

    if value in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[value]

    lowered = value.lower()

    for title, slug in CATEGORY_ALIASES.items():
        if title.lower() == lowered:
            return slug

    return value


def normalize_categories(raw_doc: dict[str, Any]) -> list[str]:
    raw_categories: list[Any] = []

    categories = raw_doc.get("categories")

    if isinstance(categories, list):
        raw_categories.extend(categories)

    category = raw_doc.get("category")

    if category:
        raw_categories.append(category)

    result: list[str] = []

    for raw in raw_categories:
        slug = normalize_category_slug(raw)

        if slug and slug not in result:
            result.append(slug)

    return result or ["it"]


def read_json_documents() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        print("[import_documents_json] data/documents.json не найден")
        return []

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[import_documents_json] documents.json повреждён: {exc}")
        return []

    if not isinstance(data, list):
        print("[import_documents_json] documents.json должен быть списком")
        return []

    return [item for item in data if isinstance(item, dict)]


def get_or_create_category(db, slug: str) -> Category:
    category = db.query(Category).filter(Category.slug == slug).first()

    if category:
        return category

    category_info = CATEGORY_BY_SLUG.get(slug, {})

    category = Category(
        slug=slug,
        title=category_info.get("title", slug),
        number=category_info.get("number") or None,
        description=category_info.get("description") or None,
        example=category_info.get("example") or None,
        color=category_info.get("color") or None,
        parent_slug=category_info.get("parent_slug") or None,
    )

    db.add(category)
    db.flush()

    return category


def find_existing_document(db, doc_id: str, source_url: str) -> Document | None:
    document = db.query(Document).filter(Document.id == doc_id).first()

    if document:
        return document

    if source_url:
        document = db.query(Document).filter(Document.source_url == source_url).first()

    return document


def upsert_document(db, raw_doc: dict[str, Any]) -> bool:
    doc_id = clean(raw_doc.get("id"))
    source_url = clean(raw_doc.get("source_url"))

    if not doc_id:
        if not source_url:
            return False

        doc_id = make_id_from_url(source_url)

    doc_id = doc_id[:200]

    document = find_existing_document(db, doc_id, source_url)
    is_new = document is None

    if document is None:
        document = Document(id=doc_id)
        db.add(document)

    title = clean(raw_doc.get("title")) or "Без названия"

    document.title = title
    document.short_title = clean(raw_doc.get("short_title")) or title[:160]

    document.doc_type = clean(raw_doc.get("doc_type") or raw_doc.get("type")) or "Документ"
    document.number = clean(raw_doc.get("number")) or None

    document.date = clean(raw_doc.get("date")) or None
    document.adopted_at = clean(raw_doc.get("adopted_at")) or None
    document.published_at = clean(raw_doc.get("published_at")) or None

    document.authority = clean(raw_doc.get("authority")) or None
    document.status = clean(raw_doc.get("status")) or "загружен"

    document.summary = clean(raw_doc.get("summary")) or None
    document.content = clean(raw_doc.get("content")) or None

    document.source = clean(raw_doc.get("source")) or None
    document.source_name = clean(raw_doc.get("source_name")) or None
    document.source_url = source_url or None

    document.file_path = clean(raw_doc.get("file_path")) or None
    document.parser = clean(raw_doc.get("parser")) or None

    document.is_parsed = bool(raw_doc.get("is_parsed", True))
    document.is_downloaded = bool(
        raw_doc.get("is_downloaded", raw_doc.get("downloaded", False))
    )

    document.updated_at = datetime.utcnow()

    category_slugs = normalize_categories(raw_doc)
    document.categories = [
        get_or_create_category(db, slug)
        for slug in category_slugs
    ]

    db.flush()

    return is_new


def import_documents() -> None:
    init_db()

    documents = read_json_documents()

    db = SessionLocal()

    added = 0
    updated = 0
    skipped = 0

    try:
        for raw_doc in documents:
            try:
                is_new = upsert_document(db, raw_doc)
                db.commit()

                if is_new:
                    added += 1
                else:
                    updated += 1

            except Exception as exc:
                db.rollback()
                skipped += 1

                title = raw_doc.get("title") or raw_doc.get("source_url") or "без названия"

                print(
                    "[import_documents_json] SKIP: "
                    f"{title} -> {exc}"
                )

    finally:
        db.close()

    print(
        "[import_documents_json] Готово: "
        f"добавлено={added}, обновлено={updated}, пропущено={skipped}"
    )


if __name__ == "__main__":
    import_documents()