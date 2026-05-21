import re
from html import unescape
from typing import Any

import httpx

from app.services.category_classifier import classify_document


BASE_URL = "http://publication.pravo.gov.ru"
DOCUMENTS_API_URL = f"{BASE_URL}/api/Documents"
DOCUMENT_API_URL = f"{BASE_URL}/api/Document"
ALLOWED_API_PAGE_SIZES = [10, 30, 100, 200]


def normalize_api_page_size(page_size: int) -> int:
    """
    publication.pravo.gov.ru не принимает произвольный PageSize.
    Разрешены только 10, 30, 100, 200.
    """
    if page_size in ALLOWED_API_PAGE_SIZES:
        return page_size

    if page_size <= 10:
        return 10

    if page_size <= 30:
        return 30

    if page_size <= 100:
        return 100

    return 200


MINISTRY_SECTIONS = {
    "transport": {
        "title": "Минтранс России",
        "block_code": "foiv275",
        "authority": "Минтранс России",
        "categories": ["transport"],
        "queries": [
            "беспилот",
            "БПЛА",
            "БАС",
            "высокоавтоматизирован",
            "высокоавтоматизированные транспортные средства",
            "интеллектуальная транспортная система",
            "интеллектуальные транспортные системы",
            "цифровая трансформация транспорт",
            "искусственный интеллект транспорт",
            "экспериментальный правовой режим транспорт",
            "автоном",
            "ИИ-водитель",
            "беспилотные логистические коридоры",
            "ИТС",
            "Чат-бот",
            "видеоаналитика",
            "машинное зрение",
        ],
    },
    "agriculture": {
        "title": "Минсельхоз России",
        "block_code": "foiv266",
        "authority": "Минсельхоз России",
        "categories": ["agriculture"],
        "queries": [
            "цифров",
            "цифровизация",
            "агропромышленный комплекс",
            "сельское хозяйство",
            "сельскохозяйственная техника",
            "автоматизирован",
            "автоматизация",
            "робот",
            "роботизация",
            "точное земледелие",
            "машинное обучение",
            "искусственный интеллект",
            "беспилот",
            "экспериментальный правовой режим",
            "автопилот",
            "нейросет",
            "прогноз",
            "цифровой мониторинг",
            "видеоаналитика",
        ],
    },
}

STRICT_RELEVANT_KEYWORDS = {
    "transport": [
        "искусственный интеллект",
        "искусственного интеллекта",
        "беспилот",
        "бпла",
        "бас",
        "беспилотная авиационная система",
        "беспилотные авиационные системы",
        "высокоавтоматизирован",
        "интеллектуальная транспортная система",
        "интеллектуальные транспортные системы",
        "цифровая трансформация",
        "экспериментальный правовой режим",
    ],
    "agriculture": [
        "искусственный интеллект",
        "искусственного интеллекта",
        "машинное обучение",
        "нейросет",
        "цифровая трансформация",
        "цифровой трансформации",
        "роботизация",
        "роботизирован",
        "роботизированная",
        "автоматизированная сельскохозяйственная техника",
        "автоматизированной сельскохозяйственной техники",
        "беспилотная сельскохозяйственная техника",
        "беспилотной сельскохозяйственной техники",
        "точное земледелие",
        "экспериментальный правовой режим",
    ],
}


STRICT_IRRELEVANT_KEYWORDS = [
    # всякие тарифы / ЖКХ / ООО «Меркурий»
    "тариф",
    "тарифов",
    "тепловую энергию",
    "водоснабжение",
    "водоотведение",
    "питьевую воду",
    "инвестиционной программы ооо",
    "ооо «меркурий»",
    'ооо "меркурий"',
    "ск меркурий",
    'статуя "меркурий',
    "статуя «меркурий",
    # ветеринарные ФГИС без ИИ
    "фгис ветис",
    "ветис",
    "цербер",
    "хорриот",
    "меркурий",
    "маркировании и учете животных",
    "учете животных",
    "содержанием животных",
    "убоем животных",
    "подконтрольных товаров",
    "утилизацией биологических отходов",
    "государственной ветеринарной службы",
    # рыболовство
    "рыболовства",
    "рыбохозяйственного бассейна",
    "водных биологических ресурсов",
    # админка / кадры / финансы
    "сведения о доходах",
    "сведения о расходах",
    "об имуществе",
    "обязательствах имущественного характера",
    "перечня должностей",
    "перечней должностей",
    "признании утратившим силу",
    "признании утратившими силу",
    "субсидии",
    "субсидий",
    "субвенции",
    "льготных кредитов",
    "государственную программу",
    "государственная программа",
]


SUPER_STRONG_KEYWORDS = [
    "искусственный интеллект",
    "искусственного интеллекта",
    "машинное обучение",
    "нейросет",
    "цифровая трансформация",
    "роботизация",
    "роботизирован",
    "беспилот",
    "бпла",
    "бас",
    "точное земледелие",
]

RELEVANT_KEYWORDS = [
    "искусственный интеллект",
    "искусственного интеллекта",
    "технологий искусственного интеллекта",
    "нейросет",
    "машинное обучение",
    "цифров",
    "цифровизац",
    "цифровой трансформац",
    "цифровая трансформац",
    "информационная система",
    "информационной системы",
    "государственная информационная система",
    "автоматизированная информационная система",
    "автоматизированной информационной системы",
    "большие данные",
    "больших данных",
    "обработка данных",
    "автоматизирован",
    "автоматизац",
    "роботизац",
    "роботизирован",
    "беспилот",
    "бпла",
    "бас",
    "беспилотная авиационная система",
    "беспилотные авиационные системы",
    "высокоавтоматизирован",
    "экспериментальный правовой режим",
    "экспериментальных правовых режим",
    "эпр",
]


IRRELEVANT_KEYWORDS = [
    "сведения о доходах",
    "сведения о расходах",
    "об имуществе",
    "обязательствах имущественного характера",
    "перечня должностей",
    "перечней должностей",
    "замещение которых влечет",
    "государственных гражданских служащих",
    "кадрового резерва",
    "государственной службы",
    "о признании утратившим силу",
    "о признании утратившими силу",
    "правила рыболовства",
    "ограничений рыболовства",
    "рыболовства водных биологических ресурсов",
    "водных биологических ресурсов",
    "рыбохозяйственного бассейна",
    "дальневосточного рыбохозяйственного бассейна",
    "льготных кредитов",
    "льготные кредиты",
    "субсидий",
    "субсидии",
    "субвенции",
    "единую субвенцию",
    "бюджетам субъектов",
    "целевых показателей эффективности",
    "регулярных и чартерных международных воздушных перевозок",
    "международных воздушных перевозок",
    "пассажиров, багажа, грузов и почты",
    "рыбное и сельское хозяйство",
    "государственную программу",
    "государственная программа",
    "внесении изменений в государственную программу",
    "показателей эффективности",
    "водных биологических ресурсов",
    "рыбохозяйственного комплекса",
]

TECH_KEYWORDS = [
    "искусственный интеллект",
    "искусственного интеллекта",
    "нейросет",
    "машинное обучение",
    "цифров",
    "цифровизац",
    "цифровой трансформац",
    "цифровая трансформац",
    "информационная система",
    "информационной системы",
    "государственная информационная система",
    "автоматизированная информационная система",
    "автоматизированной информационной системы",
    "автоматизирован",
    "автоматизац",
    "фгис",
    "большие данные",
    "больших данных",
    "робот",
    "роботизац",
    "роботизирован",
    "беспилот",
    "бпла",
    "бас",
    "высокоавтоматизирован",
    "ветис",
    "меркурий",
    "цербер",
]


BRANCH_KEYWORDS = {
    "transport": [
        "транспорт",
        "транспортн",
        "минтранс",
        "перевоз",
        "автомобильн",
        "дорожн",
        "авиацион",
        "беспилот",
        "бпла",
        "бас",
        "интеллектуальная транспортная система",
        "интеллектуальные транспортные системы",
    ],
    "agriculture": [
        "сельское хозяйство",
        "сельского хозяйства",
        "сельскохозяй",
        "минсельхоз",
        "агропромышлен",
        "апк",
        "зерно",
        "семеновод",
        "племенное животноводство",
        "животновод",
        "растениевод",
        "ветеринар",
        "ветис",
        "меркурий",
        "цербер",
    ],
}


STRONG_AI_KEYWORDS = [
    "искусственный интеллект",
    "искусственного интеллекта",
    "нейросет",
    "машинное обучение",
    "беспилот",
    "бпла",
    "бас",
    "высокоавтоматизирован",
]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, dict):
        for key in ["name", "Name", "title", "Title", "text", "Text"]:
            if value.get(key):
                return _clean_text(value.get(key))

        values = [
            str(v)
            for v in value.values()
            if v is not None and not re.fullmatch(r"[0-9a-fA-F-]{20,}", str(v))
        ]
        return " ".join(values[:3])

    if isinstance(value, list):
        return " ".join(_clean_text(item) for item in value)

    value = unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _first_value(item: dict[str, Any], keys: list[str], default: str = "") -> str:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return _clean_text(value)
    return default


def _extract_items(data: Any) -> list[dict[str, Any]]:
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


def _extract_eo_number(item: dict[str, Any]) -> str:
    return _first_value(
        item,
        [
            "eoNumber",
            "EoNumber",
            "eo_number",
            "publicationNumber",
            "PublicationNumber",
            "numberEo",
            "NumberEo",
        ],
    )


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

    match = re.search(r"\b([0-9]+-[Фф][Зз])\b", text)
    if match:
        return match.group(1)

    return ""


def _guess_doc_type(title: str) -> str:
    lower = title.lower()

    if "федеральный закон" in lower:
        return "Федеральный закон"
    if "указ президента" in lower:
        return "Указ Президента РФ"
    if "постановление" in lower:
        return "Постановление"
    if "распоряжение" in lower:
        return "Распоряжение"
    if "приказ" in lower:
        return "Приказ"

    return "НПА"


def _normalize_doc_type(value: Any, title: str) -> str:
    cleaned = _clean_text(value)

    if not cleaned:
        return _guess_doc_type(title)

    # API иногда отдаёт словарь вида "70 Приказ uuid".
    # Оставляем только человекочитаемый тип.
    known_types = [
        "Федеральный закон",
        "Указ",
        "Указ Президента РФ",
        "Постановление",
        "Постановление Правительства РФ",
        "Распоряжение",
        "Распоряжение Правительства РФ",
        "Приказ",
    ]

    for doc_type in known_types:
        if doc_type.lower() in cleaned.lower():
            return doc_type

    if re.search(r"[0-9a-fA-F-]{20,}", cleaned):
        return _guess_doc_type(title)

    return cleaned


def _is_relevant_document(doc: dict[str, Any], section_key: str) -> bool:
    """
    Строгая проверка релевантности.

    Теперь документ проходит только если:
    - в названии есть сильный признак ИИ/цифровой трансформации/роботизации/БПЛА;
    - и при этом он не похож на тарифы, ВетИС-админку, рыболовство, субсидии и т.п.
    """

    title = _clean_text(doc.get("title", "")).lower()
    doc_type = _clean_text(doc.get("doc_type") or doc.get("type") or "").lower()

    text = f" {title} {doc_type} "

    has_relevant = any(
        keyword in text for keyword in STRICT_RELEVANT_KEYWORDS.get(section_key, [])
    )

    has_super_strong = any(keyword in text for keyword in SUPER_STRONG_KEYWORDS)

    has_irrelevant = any(keyword in text for keyword in STRICT_IRRELEVANT_KEYWORDS)

    if has_irrelevant and not has_super_strong:
        return False

    return has_relevant


def _request_documents(
    client: httpx.Client,
    query: str,
    page: int,
    page_size: int,
    date_from: str,
    date_to: str = "",
) -> list[dict[str, Any]]:
    """
    Запрашивает документы через API publication.pravo.gov.ru.

    Важно:
    - PageSize должен быть только 10, 30, 100 или 200;
    - PublishDateTo не отправляем, чтобы не ловить 400 из-за будущих дат;
    - сначала пробуем DocumentText, потом Name.
    """

    page_size = normalize_api_page_size(page_size)

    request_variants = [
        {
            "DocumentText": query,
            "PublishDateFrom": date_from,
            "PageSize": page_size,
            "Index": page,
        },
        {
            "Name": query,
            "PublishDateFrom": date_from,
            "PageSize": page_size,
            "Index": page,
        },
        {
            "DocumentText": query,
            "PageSize": page_size,
            "Index": page,
        },
        {
            "Name": query,
            "PageSize": page_size,
            "Index": page,
        },
    ]

    for params in request_variants:
        try:
            response = client.get(DOCUMENTS_API_URL, params=params)

            if response.status_code != 200:
                print(f"[section_parser] API {response.status_code}: {response.url}")
                print(f"[section_parser] body: {response.text[:300]}")
                continue

            data = response.json()
            items = _extract_items(data)

            if items:
                return items

        except Exception as exc:
            print(f"[section_parser] request failed: {query} -> {exc}")
            continue

    return []


def _fetch_document_api(client: httpx.Client, eo_number: str) -> dict[str, Any] | None:
    try:
        response = client.get(DOCUMENT_API_URL, params={"eoNumber": eo_number})
        if response.status_code != 200:
            return None

        data = response.json()
        if isinstance(data, dict):
            return data

        return None
    except Exception:
        return None


def _build_document_from_api(
    item: dict[str, Any],
    eo_number: str,
    section: dict[str, Any],
    query: str,
) -> dict[str, Any]:
    title = _first_value(
        item,
        ["name", "Name", "title", "Title", "documentName", "DocumentName"],
        f"Документ № {eo_number}",
    )

    number = _first_value(
        item,
        ["number", "Number", "documentNumber", "DocumentNumber"],
        _extract_number(title),
    )

    document_date = _first_value(
        item,
        ["documentDate", "DocumentDate", "date", "Date"],
        _extract_date(title),
    )

    published_at = _first_value(
        item,
        ["publishDate", "PublishDate", "publicationDate", "PublicationDate"],
        "",
    )

    raw_doc_type = (
        item.get("documentType")
        or item.get("DocumentType")
        or item.get("type")
        or item.get("Type")
    )
    doc_type = _normalize_doc_type(raw_doc_type, title)

    authority = _first_value(
        item,
        ["signatoryAuthority", "SignatoryAuthority", "authority", "Authority"],
        section["authority"],
    )

    source_url = f"{BASE_URL}/Document/View/{eo_number}"

    doc = {
        "id": f"pravo-{eo_number}",
        "title": title,
        "short_title": title,
        "type": doc_type,
        "doc_type": doc_type,
        "number": number,
        "date": document_date or published_at,
        "adopted_at": document_date,
        "published_at": published_at,
        "authority": authority or section["authority"],
        "status": "загружен из официального API",
        "summary": f"Документ найден через тематический поиск по запросу: «{query}».",
        "source": "publication.pravo.gov.ru",
        "source_name": "Официальный интернет-портал правовой информации",
        "source_url": source_url,
        "tags": [],
        "categories": [],
        "is_parsed": True,
        "is_downloaded": False,
        "parser": "pravo_section_parser",
    }

    manual_categories = [str(category) for category in section["categories"]]

    extra_categories = []
    text_for_category = _clean_text(doc.get("title", "")).lower()

    if any(
        word in text_for_category
        for word in [
            "искусственный интеллект",
            "цифровая трансформация",
            "интеллектуальная транспортная система",
            "автоматизирован",
            "робот",
            "беспилот",
            "бпла",
            "бас",
        ]
    ):
        extra_categories.append("it")

    doc["categories"] = list(dict.fromkeys(manual_categories + extra_categories))
    return doc


def fetch_ministry_section_documents(
    section_key: str,
    limit: int = 200,
    scan_limit: int = 1500,
    page_size: int = 100,
    date_from: str = "2010-01-01",
    date_to: str = "",
) -> list[dict[str, Any]]:
    """
    Ищет документы по отрасли через API publication.pravo.gov.ru.

    """
    if section_key not in MINISTRY_SECTIONS:
        raise ValueError(f"Неизвестный раздел: {section_key}")

    section = MINISTRY_SECTIONS[section_key]

    headers = {
        "User-Agent": "Mozilla/5.0 normative-ai-catalog/0.1",
        "Accept": "application/json,text/html,*/*",
    }

    timeout = httpx.Timeout(30.0)

    documents: list[dict[str, Any]] = []
    seen_eo_numbers: set[str] = set()
    checked_count = 0

    with httpx.Client(
        headers=headers, timeout=timeout, follow_redirects=True
    ) as client:
        for query in section["queries"]:
            if len(documents) >= limit or checked_count >= scan_limit:
                break

            print(f"[section_parser] Поиск: {section['title']} / {query}")

            page = 1

            while len(documents) < limit and checked_count < scan_limit:
                items = _request_documents(
                    client=client,
                    query=query,
                    page=page,
                    page_size=page_size,
                    date_from=date_from,
                    date_to=date_to,
                )

                if not items:
                    break

                print(
                    f"[section_parser] query='{query}', page={page}, "
                    f"получено: {len(items)}"
                )

                for item in items:
                    if len(documents) >= limit or checked_count >= scan_limit:
                        break

                    checked_count += 1

                    eo_number = _extract_eo_number(item)
                    if not eo_number:
                        continue

                    if eo_number in seen_eo_numbers:
                        continue

                    seen_eo_numbers.add(eo_number)

                    full_item = _fetch_document_api(client, eo_number) or item
                    doc = _build_document_from_api(
                        item=full_item,
                        eo_number=eo_number,
                        section=section,
                        query=query,
                    )

                    if not _is_relevant_document(doc, section_key):
                        print(f"[section_parser] SKIP irrelevant: {doc['title'][:120]}")
                        continue

                    documents.append(doc)
                    print(f"[section_parser] OK relevant: {doc['title'][:120]}")

                if len(items) < page_size:
                    break

                page += 1

    print(
        f"[section_parser] {section['title']}: "
        f"проверено {checked_count}, сохранено {len(documents)}"
    )

    return documents
