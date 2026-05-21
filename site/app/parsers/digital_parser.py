from __future__ import annotations

import re
import time
import random
from html import unescape
from typing import Any

import httpx

from app.services.category_classifier import classify_document


BASE_URL = "https://digital.gov.ru"
GATSBY_API = "https://digital.gov.ru/api/digital/v2/page-data"

AUTHORITY = "Министерство цифрового развития, связи и массовых коммуникаций РФ"
SOURCE_NAME = "Минцифры России"

SEARCH_QUERIES = [
    "искусственный интеллект",
    "нейротехнологии",
    "машинное обучение",
    "нейросети",
    "большие данные",
    "цифровая трансформация",
    "цифровая экономика",
    "беспилотные",
    "компьютерное зрение",
]

RELEVANT_KEYWORDS = [
    "искусственный интеллект",
    "искусственного интеллекта",
    "технологии искусственного интеллекта",
    "нейротехнолог",
    "машинное обучение",
    "машинного обучения",
    "нейронн",
    "нейросет",
    "глубокое обучение",
    "глубокого обучения",
    "большие данные",
    "больших данных",
    "цифровая трансформация",
    "цифровой трансформации",
    "цифровая экономика",
    "цифровые двойник",
    "цифровых двойник",
    "компьютерное зрение",
    "компьютерного зрения",
    "беспилотн",
    "бпла",
]

IRRELEVANT_KEYWORDS = [
    "публичного сервитута",
    "сервитут",
    "ликвидационной комиссии",
    "ликвидационная комиссия",
    "кадрового резерва",
    "вакансии",
    "конкурс",
    "олимпиада",
    "награждении",
    "благодарность",
    "совещание",
    "семинар",
    "интеллектуальная собственность",
    "объекты интеллектуальной собственности",
    "интеллектуальные права",
    "имущественного характера",
    "сведения о доходах",
    "сведения о расходах",
    "закупк",
    "государственная тайна",
    "персональный состав",
    "состав комиссии",
]


def _clean(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, dict):
        for key in ["name", "title", "text", "post_title", "post_excerpt"]:
            if value.get(key):
                return _clean(value.get(key))
        return " ".join(_clean(v) for v in value.values() if v is not None)

    if isinstance(value, list):
        return " ".join(_clean(item) for item in value)

    text = unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_date(text: str) -> str:
    match = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
    if match:
        return match.group(1)

    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)

    return ""


def _extract_number(text: str) -> str:
    match = re.search(r"№\s*([0-9]+(?:-[А-Яа-яA-Za-z]+)?(?:/[0-9]+)?)", text)
    if match:
        return match.group(1)

    return ""


def _guess_doc_type(title: str, hint: str = "") -> str:
    text = f"{title} {hint}".lower()

    rules = [
        ("федеральный закон", "Федеральный закон"),
        ("указ президента", "Указ Президента РФ"),
        ("постановление правительства", "Постановление Правительства РФ"),
        ("распоряжение правительства", "Распоряжение Правительства РФ"),
        ("приказ", "Приказ"),
        ("концепция", "Концепция"),
        ("стратегия", "Стратегия"),
        ("программа", "Программа"),
        ("дорожная карта", "Дорожная карта"),
        ("положение", "Положение"),
        ("методические рекомендации", "Методические рекомендации"),
        ("распоряжение", "Распоряжение"),
        ("национальный проект", "Национальный проект"),
        ("план мероприятий", "План мероприятий"),
    ]

    for keyword, doc_type in rules:
        if keyword in text:
            return doc_type

    return hint or "Документ"


def _make_id(source_url: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9а-яА-Я]+", "-", source_url).strip("-").lower()
    return f"digital-{safe[:120]}"


def _is_relevant(doc: dict[str, Any]) -> bool:
    """
    Проверяет релевантность документа по его собственному содержимому.

    ВАЖНО:
    Не используем поисковый запрос как признак релевантности.
    Иначе любой документ из выдачи по запросу «искусственный интеллект»
    будет считаться подходящим.
    """

    tag_names = doc.get("_tag_names") or []

    text = " ".join(
        [
            _clean(doc.get("title")),
            _clean(doc.get("summary")),
            _clean(doc.get("doc_type")),
            _clean(tag_names),
        ]
    ).lower()

    if any(bad in text for bad in IRRELEVANT_KEYWORDS):
        return False

    return any(keyword in text for keyword in RELEVANT_KEYWORDS)


def _make_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://digital.gov.ru/documents/",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Connection": "close",
        },
        timeout=httpx.Timeout(
            connect=90.0,
            read=90.0,
            write=30.0,
            pool=30.0,
        ),
        follow_redirects=True,

        # Для локальной разработки на Windows иногда помогает,
        # если SSL/прокси/антивирус мешают нормальному handshake.
        verify=False,

        # Отключаем чтение системных proxy env.
        # Если у тебя доступ к digital.gov.ru работает только через системный прокси,
        # поставь тут True.
        trust_env=False,
    )


def _api_get(client: httpx.Client, path: str) -> dict[str, Any] | None:
    """
    Запрос к API Минцифры с повторами.

    digital.gov.ru иногда долго отвечает или рвёт TLS-соединение,
    поэтому один неудачный запрос не должен ломать весь парсер.
    """

    for attempt in range(1, 4):
        try:
            response = client.get(GATSBY_API, params={"path": path})

            if response.status_code == 404:
                return None

            response.raise_for_status()

            data = response.json()

            if isinstance(data, dict):
                return data

            return None

        except httpx.ConnectTimeout as exc:
            print(
                f"[digital_parser] timeout connect "
                f"path={path!r}, attempt={attempt}/3: {exc}"
            )

        except httpx.ReadTimeout as exc:
            print(
                f"[digital_parser] timeout read "
                f"path={path!r}, attempt={attempt}/3: {exc}"
            )

        except httpx.ConnectError as exc:
            print(
                f"[digital_parser] connect error "
                f"path={path!r}, attempt={attempt}/3: {exc}"
            )

        except Exception as exc:
            print(
                f"[digital_parser] API error "
                f"path={path!r}, attempt={attempt}/3: {exc}"
            )

        time.sleep(2 + attempt + random.random())

    return None


def _has_more(data: dict[str, Any]) -> bool:
    return str(data.get("showMore", "")).lower() == "true"


def _build_doc_from_item(item: dict[str, Any]) -> dict[str, Any] | None:
    post_name = _clean(item.get("post_name") or "")
    numeric_id = str(item.get("id") or "").strip()

    if post_name:
        source_url = f"{BASE_URL}/ru/documents/{post_name}/"
    elif numeric_id:
        source_url = f"{BASE_URL}/ru/documents/{numeric_id}/"
    else:
        return None

    type_info = item.get("type") or {}

    if isinstance(type_info, dict):
        type_name = _clean(type_info.get("name") or "")
    else:
        type_name = _clean(type_info)

    post_title = _clean(item.get("post_title") or "")
    excerpt = _clean(item.get("post_excerpt") or "")
    number = _clean(item.get("number") or "")

    # У digital.gov.ru часто post_title = тип документа, а post_excerpt = название/анонс.
    if excerpt:
        title = excerpt
    elif post_title and number:
        title = f"{post_title} № {number}"
    else:
        title = post_title or type_name or source_url

    if not number:
        number = _extract_number(title)

    date_raw = _clean(item.get("date_signing") or item.get("date_publication") or "")
    date_value = _extract_date(date_raw) or date_raw

    accepted_info = item.get("accepted") or {}
    if isinstance(accepted_info, dict):
        authority = _clean(accepted_info.get("name") or "")
    else:
        authority = ""

    authority = authority or AUTHORITY

    tags_raw = item.get("tags") or []
    tag_names: list[str] = []

    if isinstance(tags_raw, list):
        for tag in tags_raw:
            if isinstance(tag, dict):
                tag_name = _clean(tag.get("name") or "")
                if tag_name:
                    tag_names.append(tag_name)

    doc_type = _guess_doc_type(title, type_name or post_title)

    doc = {
        "id": _make_id(source_url),
        "title": title,
        "short_title": title[:160] if len(title) > 160 else title,
        "type": doc_type,
        "doc_type": doc_type,
        "number": number,
        "date": date_value,
        "adopted_at": date_value,
        "published_at": "",
        "authority": authority,
        "status": "загружен из API Минцифры",
        "summary": title,
        "source": "digital.gov.ru",
        "source_name": SOURCE_NAME,
        "source_url": source_url,
        "tags": [],
        "categories": [],
        "is_parsed": True,
        "is_downloaded": False,
        "parser": "digital_parser",
        "_wp_id": numeric_id,
        "_post_name": post_name,
        "_tag_names": tag_names,
    }

    categories = ["it"]
    categories.extend(classify_document(doc))
    doc["categories"] = list(dict.fromkeys(categories))

    return doc


def _parse_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Превращает сырые элементы API в наши документы.

    Здесь НЕ фильтруем релевантность.
    Фильтрация выполняется отдельно, чтобы в логах было видно:
    сколько API реально вернул и сколько мы оставили.
    """

    raw_items = data.get("documents")

    if not isinstance(raw_items, list):
        return []

    docs: list[dict[str, Any]] = []

    for item in raw_items:
        if not isinstance(item, dict):
            continue

        doc = _build_doc_from_item(item)

        if doc:
            docs.append(doc)

    return docs

def _add_unique(
    docs: list[dict[str, Any]],
    seen_urls: set[str],
    result: list[dict[str, Any]],
) -> int:
    added = 0

    for doc in docs:
        source_url = str(doc.get("source_url") or "")

        if not source_url:
            continue

        if source_url in seen_urls:
            continue

        seen_urls.add(source_url)
        result.append(doc)
        added += 1

    return added

def _fetch_search_query(
    client: httpx.Client,
    query: str,
    max_pages: int,
    seen_urls: set[str],
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        if page == 1:
            path = f"documents?&search={query}"
        else:
            path = f"documents?&search={query}&page={page}"

        data = _api_get(client, path)

        if not data:
            break

        raw_docs = _parse_items(data)

        relevant_docs = [
            doc for doc in raw_docs
            if _is_relevant(doc)
        ]

        added_on_page = _add_unique(
            docs=relevant_docs,
            seen_urls=seen_urls,
            result=found,
        )

        print(
            f"[digital_parser] query='{query}', page={page}, "
            f"сырых={len(raw_docs)}, релевантных={len(relevant_docs)}, "
            f"добавлено={added_on_page}"
        )

        if not raw_docs:
            break

        if not _has_more(data):
            break

        time.sleep(0.25)

    return found

def _fetch_catalog_pages(
    client: httpx.Client,
    max_pages: int,
    seen_urls: set[str],
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    print(f"[digital_parser] Сканируем каталог Минцифры: максимум {max_pages} стр.")

    for page in range(1, max_pages + 1):
        if page == 1:
            path = "/documents/"
        else:
            path = f"documents?&page={page}"

        data = _api_get(client, path)

        if not data:
            break

        raw_docs = _parse_items(data)

        relevant_docs = [
            doc for doc in raw_docs
            if _is_relevant(doc)
        ]

        added_on_page = _add_unique(
            docs=relevant_docs,
            seen_urls=seen_urls,
            result=found,
        )

        print(
            f"[digital_parser] catalog page={page}, "
            f"сырых={len(raw_docs)}, релевантных={len(relevant_docs)}, "
            f"добавлено={added_on_page}"
        )

        if not raw_docs:
            break

        if not _has_more(data):
            break

        time.sleep(0.25)

    return found

def fetch_digital_gov_documents(
    max_pages_per_query: int = 10,
    max_catalog_pages: int = 50,
) -> list[dict[str, Any]]:
    """
    Возвращает документы Минцифры по теме ИИ/цифровизации.

    Ничего сама не пишет в documents.json.
    Сохранение делает общий document_service.add_parsed_documents().
    """

    all_docs: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    with _make_client() as client:
        # 1. Сначала сканируем общий каталог.
        catalog_docs = _fetch_catalog_pages(
            client=client,
            max_pages=max_catalog_pages,
            seen_urls=seen_urls,
        )
        all_docs.extend(catalog_docs)

        # 2. Потом добираем документы через поиск.
        for query in SEARCH_QUERIES:
            print(f"[digital_parser] Поиск: {query}")

            docs = _fetch_search_query(
                client=client,
                query=query,
                max_pages=max_pages_per_query,
                seen_urls=seen_urls,
            )

            all_docs.extend(docs)
            time.sleep(0.3)

    print(f"[digital_parser] Всего релевантных документов: {len(all_docs)}")
    return all_docs