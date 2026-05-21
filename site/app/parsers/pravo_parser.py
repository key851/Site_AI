from datetime import date, timedelta
from typing import Any

import httpx

from app.services.category_classifier import classify_document


PRAVO_API_URL = "http://publication.pravo.gov.ru/api/Documents"

SEARCH_KEYWORDS = [
    "искусственный интеллект",
    "цифров",
    "информационн",
    "персональные данные",
    "экспериментальный правовой режим",
    "беспилот",
    "БПЛА",
    "БАС",
    "высокоавтоматизирован",
    "сельское хозяйство",
    "агропромышлен",
    "растениевод",
    "животновод",
]


def _first_value(item: dict[str, Any], keys: list[str], default: str = "") -> str:
    for key in keys:
        value = item.get(key)
        if value is not None and value != "":
            return str(value)
    return default


def _extract_items(data: Any) -> list[dict[str, Any]]:
    """
    У API могут отличаться названия контейнера с результатами,
    поэтому ищем список документов максимально терпимо.
    """
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    if isinstance(data, dict):
        for key in [
            "items",
            "Items",
            "documents",
            "Documents",
            "data",
            "Data",
            "results",
            "Results",
            "list",
            "List",
        ]:
            value = data.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        for value in data.values():
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

    return []


def _normalize_pravo_item(
    item: dict[str, Any],
    keyword: str = "",
    search_mode: str = "keyword",
) -> dict[str, Any]:
    """
    Приводим документ с pravo.gov.ru к нашему внутреннему формату.
    """

    eo_number = _first_value(
        item,
        [
            "eoNumber",
            "EoNumber",
            "eo_number",
            "externalNumber",
            "ExternalNumber",
            "publicationNumber",
            "PublicationNumber",
        ],
    )

    title = _first_value(
        item,
        [
            "name",
            "Name",
            "title",
            "Title",
            "documentName",
            "DocumentName",
            "docName",
            "DocName",
        ],
        "Документ без названия",
    )

    number = _first_value(
        item,
        [
            "number",
            "Number",
            "documentNumber",
            "DocumentNumber",
            "docNumber",
            "DocNumber",
        ],
    )

    published_at = _first_value(
        item,
        [
            "publishDate",
            "PublishDate",
            "publicationDate",
            "PublicationDate",
            "publishedAt",
            "PublishedAt",
        ],
    )

    document_date = _first_value(
        item,
        [
            "documentDate",
            "DocumentDate",
            "date",
            "Date",
            "signDate",
            "SignDate",
        ],
    )

    authority = _first_value(
        item,
        [
            "signatoryAuthority",
            "SignatoryAuthority",
            "authority",
            "Authority",
            "organ",
            "Organ",
        ],
    )

    doc_type = _first_value(
        item,
        [
            "documentType",
            "DocumentType",
            "type",
            "Type",
            "kind",
            "Kind",
        ],
        "НПА",
    )

    if eo_number:
        source_url = f"http://publication.pravo.gov.ru/document/{eo_number}"
        doc_id = f"pravo-{eo_number}"
    else:
        safe_key = abs(hash(title + number + published_at + keyword + search_mode))
        source_url = "http://publication.pravo.gov.ru/"
        doc_id = f"pravo-{safe_key}"

    summary_parts = ["Документ найден на publication.pravo.gov.ru."]
    if keyword:
        summary_parts.append(f"Ключевое слово: «{keyword}».")
    summary_parts.append(f"Режим поиска: {search_mode}.")

    doc = {
        "id": doc_id,
        "title": title,
        "short_title": title,
        "type": doc_type,
        "doc_type": doc_type,
        "number": number,
        "date": document_date or published_at,
        "adopted_at": document_date,
        "published_at": published_at,
        "authority": authority,
        "status": "найден парсером",
        "summary": " ".join(summary_parts),
        "source": "publication.pravo.gov.ru",
        "source_name": "Официальный интернет-портал правовой информации",
        "source_url": source_url,
        "tags": ["pravo.gov.ru", keyword, search_mode],
        "is_parsed": True,
        "is_downloaded": False,
        "parser": "pravo_parser",
        "category": "Автоматически найденные",
        "categories": [],
    }

    doc["categories"] = classify_document(doc)
    return doc


def _request_json(client: httpx.Client, params: dict[str, Any]) -> Any | None:
    """
    Выполняет запрос и печатает нормальную диагностику, если API вернул 400/500.
    """
    try:
        response = client.get(PRAVO_API_URL, params=params)
    except Exception as exc:
        print(f"[pravo_parser] Ошибка соединения: {exc}")
        return None

    if response.status_code != 200:
        print("[pravo_parser] API вернул ошибку")
        print(f"  status: {response.status_code}")
        print(f"  url: {response.url}")
        print(f"  body: {response.text[:500]}")
        return None

    try:
        return response.json()
    except Exception as exc:
        print(f"[pravo_parser] Не удалось разобрать JSON: {exc}")
        print(f"  body: {response.text[:500]}")
        return None


def fetch_pravo_documents(days_back: int = 365, page_size: int = 20) -> list[dict[str, Any]]:
    """
    Устойчивая MVP-версия парсера.

    1. Ищет по ключевым словам через DocumentText.
    2. Отдельно берёт свежие документы ФОИВ через PeriodType=daily.
    3. Не использует проблемную комбинацию Block + DocumentText + сортировка.
    """
    date_from = date.today() - timedelta(days=days_back)

    found: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    timeout = httpx.Timeout(20.0)

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        # 1. Поиск по ключевым словам.
        for keyword in SEARCH_KEYWORDS:
            params = {
                "DocumentText": keyword,
                "PublishDateFrom": date_from.isoformat(),
                "PageSize": page_size,
                "Index": 1,
            }

            data = _request_json(client, params)
            if data is None:
                # fallback: иногда поиск по названию мягче, чем полнотекстовый поиск
                params = {
                    "Name": keyword,
                    "PublishDateFrom": date_from.isoformat(),
                    "PageSize": page_size,
                    "Index": 1,
                }
                data = _request_json(client, params)

            if data is None:
                continue

            items = _extract_items(data)

            for item in items:
                doc = _normalize_pravo_item(
                    item,
                    keyword=keyword,
                    search_mode="keyword",
                )

                doc_key = doc.get("id") or doc.get("source_url") or doc.get("title")
                if doc_key in seen_ids:
                    continue

                seen_ids.add(doc_key)
                found.append(doc)

        # 2. Свежие документы ФОИВ за день.
        daily_params = {
            "Block": "federal_authorities",
            "PeriodType": "daily",
            "PageSize": 200,
            "Index": 1,
        }

        data = _request_json(client, daily_params)
        if data is not None:
            items = _extract_items(data)

            for item in items:
                doc = _normalize_pravo_item(
                    item,
                    keyword="daily",
                    search_mode="daily_federal_authorities",
                )

                # daily-запрос широкий, поэтому фильтруем уже у себя
                text = " ".join(
                    [
                        doc.get("title", ""),
                        doc.get("summary", ""),
                        doc.get("authority", ""),
                        " ".join(doc.get("tags", [])),
                    ]
                ).lower()

                if not any(word.lower() in text for word in SEARCH_KEYWORDS):
                    continue

                doc_key = doc.get("id") or doc.get("source_url") or doc.get("title")
                if doc_key in seen_ids:
                    continue

                seen_ids.add(doc_key)
                found.append(doc)

    print(f"[pravo_parser] Найдено документов: {len(found)}")
    return found