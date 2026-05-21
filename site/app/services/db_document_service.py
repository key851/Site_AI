from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from app.core.categories import CATEGORIES, CATEGORY_BY_SLUG
from app.database import SessionLocal
from app.models import Category, Document


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


def _clean(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _make_id_from_url(source_url: str) -> str:
    value = source_url.replace("https://", "").replace("http://", "")
    value = re.sub(r"[^a-zA-Z0-9а-яА-Я]+", "-", value)
    value = value.strip("-").lower()
    return value[:180] or "document-without-id"


def normalize_category_slug(value: Any) -> str:
    value = _clean(value)

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


def get_category_title(slug: str | None) -> str:
    if not slug:
        return "Без раздела"

    slug = normalize_category_slug(slug)

    if slug in CATEGORY_BY_SLUG:
        return CATEGORY_BY_SLUG[slug].get("title", slug)

    return slug


def get_category_options() -> list[dict[str, Any]]:
    return CATEGORIES


def _document_to_dict(document: Document) -> dict[str, Any]:
    categories = [category.slug for category in document.categories]

    return {
        "id": document.id,
        "title": document.title,
        "short_title": document.short_title or document.title,
        "type": document.doc_type or "Документ",
        "doc_type": document.doc_type or "Документ",
        "number": document.number or "",
        "date": document.date or "",
        "adopted_at": document.adopted_at or "",
        "published_at": document.published_at or "",
        "authority": document.authority or "",
        "status": document.status or "",
        "summary": document.summary or "",
        "content": document.content or "",
        "source": document.source or "",
        "source_name": document.source_name or "",
        "source_url": document.source_url or "",
        "file_path": document.file_path or "",
        "parser": document.parser or "",
        "categories": categories,
        "category": categories[0] if categories else "",
        "tags": [],
        "is_parsed": document.is_parsed,
        "is_downloaded": document.is_downloaded,
    }


def _get_or_create_category(db, slug: str) -> Category:
    slug = normalize_category_slug(slug)

    category = db.query(Category).filter(Category.slug == slug).first()

    if category:
        return category

    info = CATEGORY_BY_SLUG.get(slug, {})

    category = Category(
        slug=slug,
        title=info.get("title", slug),
        number=info.get("number") or None,
        description=info.get("description") or None,
        example=info.get("example") or None,
        color=info.get("color") or None,
        parent_slug=info.get("parent_slug") or None,
    )

    db.add(category)
    db.flush()

    return category


def _find_existing_document(db, doc_id: str, source_url: str) -> Document | None:
    document = db.query(Document).filter(Document.id == doc_id).first()

    if document:
        return document

    if source_url:
        return db.query(Document).filter(Document.source_url == source_url).first()

    return None


def _upsert_document(db, raw_doc: dict[str, Any]) -> bool:
    doc_id = _clean(raw_doc.get("id"))
    source_url = _clean(raw_doc.get("source_url"))

    if not doc_id:
        if not source_url:
            return False

        doc_id = _make_id_from_url(source_url)

    doc_id = doc_id[:200]

    document = _find_existing_document(db, doc_id, source_url)
    is_new = document is None

    if document is None:
        document = Document(id=doc_id)
        db.add(document)

    title = _clean(raw_doc.get("title")) or "Без названия"

    document.title = title
    document.short_title = _clean(raw_doc.get("short_title")) or title[:160]

    document.doc_type = _clean(raw_doc.get("doc_type") or raw_doc.get("type")) or "Документ"
    document.number = _clean(raw_doc.get("number")) or None

    document.date = _clean(raw_doc.get("date")) or None
    document.adopted_at = _clean(raw_doc.get("adopted_at")) or None
    document.published_at = _clean(raw_doc.get("published_at")) or None

    document.authority = _clean(raw_doc.get("authority")) or None
    document.status = _clean(raw_doc.get("status")) or "загружен"

    document.summary = _clean(raw_doc.get("summary")) or None
    document.content = _clean(raw_doc.get("content")) or None

    document.source = _clean(raw_doc.get("source")) or None
    document.source_name = _clean(raw_doc.get("source_name")) or None
    document.source_url = source_url or None

    document.file_path = _clean(raw_doc.get("file_path")) or None
    document.parser = _clean(raw_doc.get("parser")) or None

    document.is_parsed = bool(raw_doc.get("is_parsed", True))
    document.is_downloaded = bool(
        raw_doc.get("is_downloaded", raw_doc.get("downloaded", False))
    )

    document.updated_at = datetime.utcnow()

    category_slugs = normalize_categories(raw_doc)
    document.categories = [
        _get_or_create_category(db, slug)
        for slug in category_slugs
    ]

    db.flush()

    return is_new


def add_parsed_documents(documents: list[dict[str, Any]]) -> int:
    """
    Добавляет документы из парсеров в PostgreSQL.
    Возвращает количество новых документов.
    """

    if not documents:
        return 0

    db = SessionLocal()
    added = 0

    try:
        for raw_doc in documents:
            try:
                is_new = _upsert_document(db, raw_doc)

                if is_new:
                    added += 1

            except Exception as exc:
                db.rollback()
                title = raw_doc.get("title") or raw_doc.get("source_url") or "без названия"
                print(f"[db_document_service] SKIP: {title} -> {exc}")
                continue

        db.commit()
        return added

    finally:
        db.close()


def get_all_documents() -> list[dict[str, Any]]:
    db = SessionLocal()

    try:
        documents = (
            db.query(Document)
            .options(selectinload(Document.categories))
            .order_by(Document.created_at.desc())
            .all()
        )

        return [_document_to_dict(document) for document in documents]

    finally:
        db.close()


def get_document(document_id: str) -> dict[str, Any] | None:
    db = SessionLocal()

    try:
        document = (
            db.query(Document)
            .options(selectinload(Document.categories))
            .filter(Document.id == str(document_id))
            .first()
        )

        if document is None:
            return None

        return _document_to_dict(document)

    finally:
        db.close()


def get_documents_by_category(category_slug: str) -> list[dict[str, Any]]:
    selected_category = normalize_category_slug(category_slug)

    db = SessionLocal()

    try:
        documents = (
            db.query(Document)
            .options(selectinload(Document.categories))
            .join(Document.categories)
            .filter(Category.slug == selected_category)
            .order_by(Document.created_at.desc())
            .all()
        )

        return [_document_to_dict(document) for document in documents]

    finally:
        db.close()


def filter_documents(
    query: str = "",
    category: str = "",
    doc_type: str = "",
    status: str = "",
) -> list[dict[str, Any]]:
    query = (query or "").strip()
    category = normalize_category_slug(category)
    doc_type = (doc_type or "").strip()
    status = (status or "").strip()

    db = SessionLocal()

    try:
        db_query = (
            db.query(Document)
            .options(selectinload(Document.categories))
        )

        if category:
            db_query = db_query.join(Document.categories).filter(Category.slug == category)

        if doc_type:
            db_query = db_query.filter(Document.doc_type == doc_type)

        if status:
            db_query = db_query.filter(Document.status == status)

        if query:
            like_query = f"%{query}%"

            db_query = db_query.filter(
                or_(
                    Document.title.ilike(like_query),
                    Document.short_title.ilike(like_query),
                    Document.number.ilike(like_query),
                    Document.summary.ilike(like_query),
                    Document.authority.ilike(like_query),
                )
            )

        documents = db_query.order_by(Document.created_at.desc()).all()

        return [_document_to_dict(document) for document in documents]

    finally:
        db.close()


def get_doc_type_options() -> list[str]:
    db = SessionLocal()

    try:
        rows = (
            db.query(Document.doc_type)
            .filter(Document.doc_type.isnot(None))
            .distinct()
            .order_by(Document.doc_type)
            .all()
        )

        return [row[0] for row in rows if row[0]]

    finally:
        db.close()


def get_status_options() -> list[str]:
    db = SessionLocal()

    try:
        rows = (
            db.query(Document.status)
            .filter(Document.status.isnot(None))
            .distinct()
            .order_by(Document.status)
            .all()
        )

        return [row[0] for row in rows if row[0]]

    finally:
        db.close()