from __future__ import annotations

import re
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx

from app.services.category_classifier import classify_document


RST_AI_STANDARDS_URL = "https://www.rst.gov.ru/portal/gost/home/standarts/aistandarts"
PROTECT_GOST_SEARCH_URL = "https://protect.gost.ru/gost/?q="

SOURCE_NAME = "Росстандарт"
AUTHORITY = "Федеральное агентство по техническому регулированию и метрологии"

PDF_DIR = Path("storage/documents/gost")


STANDARD_PATTERN = re.compile(
    r"\b(?P<prefix>ГОСТ\s+Р|ПНСТ|ГОСТ\s+ISO/IEC|ГОСТ\s+Р\s+ИСО/МЭК|ГОСТ\s+Р\s+ИСО)\.?\s*(?P<number>[0-9][0-9A-Za-zА-Яа-я./-]*-\d{4})\b",
    re.IGNORECASE,
)

NUMBER_ONLY_PATTERN = re.compile(
    r"\b(?P<number>[0-9][0-9A-Za-zА-Яа-я./-]*-\d{4})\b"
)

PREFIX_ONLY = {"ГОСТ Р", "ПНСТ", "ГОСТ ISO/IEC", "ГОСТ Р ИСО/МЭК", "ГОСТ Р ИСО"}


def _clean(value: Any) -> str:
    if value is None:
        return ""

    text = unescape(str(value))
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _html_to_lines(html: str) -> list[str]:
    html = re.sub(
        r"(?i)<\s*(br|/p|/div|/tr|/td|/th|/li|/h1|/h2|/h3|/h4)\s*/?\s*>",
        "\n",
        html,
    )
    text = _clean(html)

    raw_lines = re.split(r"\n| {2,}", text)

    lines = []

    for line in raw_lines:
        line = re.sub(r"\s+", " ", line).strip(" \t\r\n;")

        if line:
            lines.append(line)

    return lines


def _extract_links(html: str, base_url: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    for match in re.finditer(
        r'<a[^>]+href=["\'](?P<href>[^"\']+)["\'][^>]*>(?P<text>[\s\S]*?)</a>',
        html,
        flags=re.IGNORECASE,
    ):
        href = match.group("href")
        text = _clean(match.group("text"))

        if not href:
            continue

        result.append(
            {
                "href": urljoin(base_url, href),
                "text": text,
            }
        )

    return result


def _normalize_designation(prefix: str, number: str) -> str:
    prefix = re.sub(r"\s+", " ", prefix.upper().replace(".", " ")).strip()
    number = number.strip()

    return f"{prefix} {number}"


def _standard_key(designation: str) -> str:
    return re.sub(r"[^0-9a-zA-Zа-яА-Я]+", "", designation).lower()


def _make_id(designation: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9а-яА-Я]+", "-", designation).strip("-").lower()
    return f"gost-{value}"[:200]


def _is_title_candidate(line: str) -> bool:
    lowered = line.lower()

    if len(line) < 18:
        return False

    if len(line) > 320:
        return False

    bad_parts = [
        "личный кабинет",
        "поиск",
        "главная",
        "карта сайта",
        "росстандарт",
        "федеральное агентство",
        "наверх",
        "скачать",
        "pdf",
        "docx",
    ]

    if any(bad in lowered for bad in bad_parts):
        return False

    return True


def _extract_title_from_line(line: str, designation: str) -> str:
    value = line

    value = STANDARD_PATTERN.sub(" ", value)
    value = value.replace(designation, " ")
    value = re.sub(r"^\d+[\).]?\s*", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .;:-")

    if _is_title_candidate(value):
        return value

    return ""


def _find_title(lines: list[str], index: int, designation: str) -> str:
    own_line_title = _extract_title_from_line(lines[index], designation)

    if own_line_title:
        return own_line_title

    # В таблицах Росстандарта часто бывает так:
    # строка с названием стоит рядом со строкой "ГОСТ Р" и номером.
    search_order = [
        index - 1,
        index - 2,
        index - 3,
        index + 1,
        index + 2,
        index + 3,
    ]

    candidates = []

    for idx in search_order:
        if idx < 0 or idx >= len(lines):
            continue

        line = lines[idx]

        if STANDARD_PATTERN.search(line):
            continue

        normalized_line = line.upper().replace(".", "").strip()

        if normalized_line in PREFIX_ONLY:
            continue

        if NUMBER_ONLY_PATTERN.fullmatch(line.strip()):
            continue

        if _is_title_candidate(line):
            candidates.append(line)

    # Сначала предпочитаем явно ИИ-шные названия.
    priority_words = [
        "искусственного интеллекта",
        "искусственный интеллект",
        "системы искусственного",
        "данных",
        "довер",
        "качество",
        "безопасность",
        "машинное обучение",
        "нейросет",
    ]

    for candidate in candidates:
        lowered = candidate.lower()

        if any(word in lowered for word in priority_words):
            return candidate

    if candidates:
        return candidates[0]

    return designation


def _choose_source_url(designation: str, links: list[dict[str, str]]) -> str:
    key = _standard_key(designation)

    for link in links:
        text_key = _standard_key(link.get("text", ""))
        href_key = _standard_key(link.get("href", ""))

        if key and (key in text_key or key in href_key):
            return link["href"]

    return f"{PROTECT_GOST_SEARCH_URL}{quote_plus(designation)}"


def _classify_gost(title: str, designation: str) -> list[str]:
    text = f"{title} {designation}".lower()

    categories = ["standardization"]

    if any(word in text for word in [
        "термин",
        "классификац",
        "техническое задание",
        "жизненный цикл",
        "системы искусственного интеллекта",
    ]):
        categories.append("base-ai-gost")

    if any(word in text for word in [
        "данн",
        "набор",
        "датасет",
        "большие данные",
        "качество данных",
        "сохранность данных",
    ]):
        categories.append("data-gost")

    if any(word in text for word in [
        "довер",
        "риск",
        "безопасн",
        "объясним",
        "прозрачн",
        "устойчив",
        "проверяем",
        "верификац",
    ]):
        categories.append("trust-security-gost")

    industry_words = {
        "transport-gost": [
            "транспорт",
            "беспилот",
            "ватс",
            "водител",
            "автомобиль",
            "дорожн",
        ],
        "agriculture-gost": [
            "сельск",
            "агроп",
            "растениевод",
            "животновод",
            "урожай",
        ],
        "it-gost": [
            "программ",
            "информационн",
            "вычисл",
            "алгоритм",
        ],
    }

    for category, words in industry_words.items():
        if any(word in text for word in words):
            categories.append("industry-gost")
            categories.append(category)

    # Если ничего узкого не нашли, но это стандарт по ИИ — кладём в базовые.
    if len(categories) == 1:
        categories.append("base-ai-gost")

    return list(dict.fromkeys(categories))


def _extract_standards_from_html(html: str, page_url: str) -> list[dict[str, Any]]:
    links = _extract_links(html, page_url)
    lines = _html_to_lines(html)

    standards: dict[str, dict[str, Any]] = {}

    # Вариант 1: префикс и номер в одной строке.
    for index, line in enumerate(lines):
        for match in STANDARD_PATTERN.finditer(line):
            designation = _normalize_designation(
                match.group("prefix"),
                match.group("number"),
            )

            key = _standard_key(designation)

            if key in standards:
                continue

            title = _find_title(lines, index, designation)
            source_url = _choose_source_url(designation, links)

            standards[key] = _build_document(
                designation=designation,
                title=title,
                source_url=source_url,
            )

    # Вариант 2: строка "ГОСТ Р", следующая строка "59277-2020".
    for index, line in enumerate(lines[:-1]):
        prefix = line.upper().replace(".", "").strip()

        if prefix not in PREFIX_ONLY:
            continue

        number_match = NUMBER_ONLY_PATTERN.search(lines[index + 1])

        if not number_match:
            continue

        designation = _normalize_designation(prefix, number_match.group("number"))
        key = _standard_key(designation)

        if key in standards:
            continue

        title = _find_title(lines, index, designation)
        source_url = _choose_source_url(designation, links)

        standards[key] = _build_document(
            designation=designation,
            title=title,
            source_url=source_url,
        )

    return list(standards.values())


def _build_document(designation: str, title: str, source_url: str) -> dict[str, Any]:
    categories = _classify_gost(title, designation)

    doc = {
        "id": _make_id(designation),
        "title": f"{designation} «{title}»" if title != designation else designation,
        "short_title": f"{designation} «{title}»" if title != designation else designation,
        "type": "ГОСТ / стандарт",
        "doc_type": "ГОСТ / стандарт",
        "number": designation,
        "date": "",
        "adopted_at": "",
        "published_at": "",
        "authority": AUTHORITY,
        "status": "найден на сайте Росстандарта",
        "summary": "Стандарт автоматически найден на официальной странице Росстандарта по направлению «Искусственный интеллект».",
        "source": "rst.gov.ru",
        "source_name": SOURCE_NAME,
        "source_url": source_url,
        "tags": [],
        "categories": categories,
        "is_parsed": True,
        "is_downloaded": False,
        "parser": "gost_parser",
    }

    # На всякий случай добавим категории общего классификатора,
    # но без риска заменить наши стандартные категории.
    auto_categories = classify_document(doc)
    doc["categories"] = list(dict.fromkeys(doc["categories"] + auto_categories))

    return doc


def _try_download_pdf(client: httpx.Client, doc: dict[str, Any]) -> dict[str, Any]:
    """
    Пытается скачать PDF, если на странице стандарта есть прямая PDF-ссылка.
    Если ссылки нет или доступ закрыт — просто оставляет source_url.
    """

    source_url = str(doc.get("source_url") or "")

    if not source_url:
        return doc

    try:
        response = client.get(source_url)
        response.raise_for_status()
    except Exception:
        return doc

    html = response.text
    pdf_links = []

    for link in _extract_links(html, source_url):
        href = link["href"]

        if ".pdf" in href.lower():
            pdf_links.append(href)

    if not pdf_links:
        return doc

    pdf_url = pdf_links[0]

    try:
        pdf_response = client.get(pdf_url)
        pdf_response.raise_for_status()

        content = pdf_response.content

        if not content.startswith(b"%PDF"):
            return doc

        PDF_DIR.mkdir(parents=True, exist_ok=True)

        file_name = re.sub(r"[^a-zA-Z0-9а-яА-Я]+", "-", str(doc["number"])).strip("-").lower()
        file_path = PDF_DIR / f"{file_name}.pdf"

        file_path.write_bytes(content)

        doc["file_path"] = str(file_path).replace("\\", "/")
        doc["is_downloaded"] = True
        doc["status"] = "PDF скачан с официального источника"

    except Exception as exc:
        print(f"[gost_parser] PDF не скачан: {doc.get('number')} -> {exc}")

    return doc


def _make_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        },
        timeout=httpx.Timeout(
            connect=60.0,
            read=60.0,
            write=30.0,
            pool=30.0,
        ),
        follow_redirects=True,
        verify=False,
        trust_env=False,
    )


def fetch_gost_documents(download_pdfs: bool = False) -> list[dict[str, Any]]:
    """
    Парсит официальную страницу Росстандарта со стандартами по ИИ.

    Ничего сам не пишет в БД.
    Сохранение делает db_document_service.add_parsed_documents().
    """

    with _make_client() as client:
        print("[gost_parser] Загружаем страницу стандартов Росстандарта")

        response = client.get(RST_AI_STANDARDS_URL)
        response.raise_for_status()

        documents = _extract_standards_from_html(
            html=response.text,
            page_url=RST_AI_STANDARDS_URL,
        )

        print(f"[gost_parser] Найдено стандартов: {len(documents)}")

        if download_pdfs:
            result = []

            for doc in documents:
                result.append(_try_download_pdf(client, doc))

            documents = result

    return documents