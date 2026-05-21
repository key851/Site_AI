from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.parsers.gost_parser import fetch_gost_documents
from app.core.categories import CATEGORY_TREE, CATEGORY_BY_SLUG
from app.core.sources import OFFICIAL_SOURCES
from app.parsers.digital_parser import fetch_digital_gov_documents
from app.parsers.pravo_parser import fetch_pravo_documents
from app.parsers.pravo_section_parser import fetch_ministry_section_documents
from app.services.db_document_service import (
    add_parsed_documents,
    filter_documents,
    get_all_documents,
    get_category_options,
    get_category_title,
    get_document,
    get_documents_by_category,
    get_doc_type_options,
    get_status_options,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["category_title"] = get_category_title

@router.post("/admin/parser/run-gost")
def run_gost_parser():
    documents = fetch_gost_documents(download_pdfs=False)
    added_count = add_parsed_documents(documents)

    return RedirectResponse(
        url=f"/updates?source=gost&found={len(documents)}&added={added_count}",
        status_code=303,
    )

@router.post("/admin/parser/run-digital")
def run_digital_parser():
    documents = fetch_digital_gov_documents(
        max_pages_per_query=5,
        max_catalog_pages=50,
    )
    added_count = add_parsed_documents(documents)

    return RedirectResponse(
        url=f"/updates?source=digital&found={len(documents)}&added={added_count}",
        status_code=303,
    )

@router.post("/admin/parser/run-mintrans")
def run_mintrans_parser():
    documents = fetch_ministry_section_documents(
        "transport",
        limit=200,
        scan_limit=1500,
        page_size=100,
    )
    added_count = add_parsed_documents(documents)

    return RedirectResponse(
        url=f"/updates?source=mintrans&found={len(documents)}&added={added_count}",
        status_code=303,
    )


@router.post("/admin/parser/run-mcx")
def run_mcx_parser():
    documents = fetch_ministry_section_documents(
        "agriculture",
        limit=200,
        scan_limit=1500,
        page_size=100,
    )
    added_count = add_parsed_documents(documents)

    return RedirectResponse(
        url=f"/updates?source=mcx&found={len(documents)}&added={added_count}",
        status_code=303,
    )

@router.post("/admin/parser/run-pravo")
def run_pravo_parser():
    documents = fetch_pravo_documents(days_back=365, page_size=10)
    added_count = add_parsed_documents(documents)

    return RedirectResponse(
        url=f"/updates?source=pravo&found={len(documents)}&added={added_count}",
        status_code=303,
    )


@router.get("/sources")
def sources(request: Request):
    return templates.TemplateResponse(
        "sources.html",
        {
            "request": request,
            "sources": OFFICIAL_SOURCES,
        },
    )


@router.get("/")
def home(request: Request):
    documents = get_all_documents()[:4]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "levels": CATEGORY_TREE,
            "documents": documents,
            "category_title": get_category_title,
        },
    )


@router.get("/catalog")
def catalog(
    request: Request,
    q: str = "",
    category: str = "",
    doc_type: str = "",
    status: str = "",
    page: int = 1,
):
    per_page = 50

    documents = filter_documents(
        query=q,
        category=category,
        doc_type=doc_type,
        status=status,
    )

    total = len(documents)
    pages_count = max((total + per_page - 1) // per_page, 1)

    page = max(1, min(page, pages_count))
    start = (page - 1) * per_page
    end = start + per_page

    paginated_documents = documents[start:end]

    return templates.TemplateResponse(
        "catalog.html",
        {
            "request": request,
            "documents": paginated_documents,
            "total": total,
            "page": page,
            "pages_count": pages_count,
            "q": q,
            "categories": get_category_options(),
            "doc_types": get_doc_type_options(),
            "statuses": get_status_options(),
            "selected_category": category,
            "selected_type": doc_type,
            "selected_status": status,
        },
    )


@router.get("/categories/{category_slug}")
def category_page(request: Request, category_slug: str):
    category = CATEGORY_BY_SLUG.get(category_slug)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")

    docs = get_documents_by_category(category_slug)
    return templates.TemplateResponse(
        "category.html",
        {
            "request": request,
            "category": category,
            "documents": docs,
            "category_title": get_category_title,
        },
    )


@router.get("/documents/{document_id}")
def document_detail(request: Request, document_id: str):
    document = get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")

    categories = document.get("categories") or []
    first_category = categories[0] if categories else None

    related = []
    if first_category:
        related = [
            doc
            for doc in get_documents_by_category(first_category)
            if str(doc.get("id", "")) != str(document_id)
        ][:3]

    return templates.TemplateResponse(
        "document.html",
        {
            "request": request,
            "document": document,
            "related_documents": related,
        },
    )


@router.get("/structure")
def structure(request: Request):
    return templates.TemplateResponse(
        "structure.html",
        {"request": request, "levels": CATEGORY_TREE, "tree_data": CATEGORY_TREE},
    )


@router.get("/standards")
def standards(request: Request):
    documents = get_all_documents()

    standards_docs = [
        doc
        for doc in documents
        if (
            "standardization" in (doc.get("categories") or [])
            or "base-ai-gost" in (doc.get("categories") or [])
            or "industry-gost" in (doc.get("categories") or [])
            or "гост" in str(doc.get("title", "")).lower()
            or "пнст" in str(doc.get("title", "")).lower()
            or "стандарт" in str(doc.get("doc_type", "")).lower()
        )
    ]

    return templates.TemplateResponse(
        "standards.html",
        {
            "request": request,
            "documents": standards_docs,
        },
    )


@router.get("/updates")
def updates(request: Request):
    parsed_docs = [doc for doc in get_all_documents() if doc.get("is_parsed")]
    return templates.TemplateResponse(
        "updates.html",
        {
            "request": request,
            "documents": parsed_docs,
            "category_title": get_category_title,
        },
    )
