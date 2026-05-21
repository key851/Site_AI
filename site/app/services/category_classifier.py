"""Простой классификатор документов по ключевым словам.

Это MVP: без машинного обучения. Зато прозрачно и быстро для защиты проекта.
Один документ может попасть сразу в несколько категорий.
"""

from typing import Any


RULES = {
    # 1. Стратегический и концептуальный уровень
    "state-ai-strategy": [
        "указ президента",
        "национальная стратегия",
        "стратегия развития искусственного интеллекта",
        "№ 490",
        "№ 124",
        "развитии искусственного интеллекта",
    ],
    "digital-policy": [
        "цифровая экономика",
        "экономика данных",
        "цифровая трансформация",
        "национальный проект",
        "федеральный проект",
    ],
    "ai-legal-concept": [
        "концепция развития регулирования",
        "робототехник",
        "регулирования ии",
        "2129-р",
    ],
    "soft-law": [
        "кодекс этики",
        "этика",
        "мягкое регулирование",
        "рекомендации",
    ],

    # 2. Законодательный уровень
    "base-laws": [
        "федеральный закон",
        "149-фз",
        "152-фз",
        "233-фз",
        "98-фз",
        "187-фз",
        "персональные данные",
        "об информации",
        "коммерческая тайна",
        "критическая информационная инфраструктура",
        "гражданский кодекс",
    ],
    "experimental-regulation": [
        "экспериментальн",
        "правовой режим",
        "экспериментальный правовой режим",
        "экспериментальных правовых режимах",
        "эпр",
        "регуляторн",
        "258-фз",
        "123-фз",
        "№ 1750",
        "№ 309",
        "высокоавтоматизирован",
    ],
    "legislative-initiatives": [
        "законопроект",
        "проект федерального закона",
        "маркировка ии-контента",
        "риск-ориентированный",
    ],

    # 4. Стандартизация
    "standardization": [
        "гост",
        "пнст",
        "стандарт",
        "росстандарт",
        "тк 164",
        "protect.gost",
        "rst.gov",
    ],
    "base-ai-gost": [
        "71476",
        "59277",
        "59276",
        "59898",
        "71752",
        "терминология",
        "классификация систем искусственного интеллекта",
        "доверие",
        "оценка качества",
        "техническое задание",
    ],
    "data-gost": [
        "качество данных",
        "метрики качества данных",
        "управление качеством данных",
        "большие данные",
        "71484",
        "848-2023",
    ],
    "industry-gost": [
        "отраслевые госты",
        "клинической медицине",
        "сельском хозяйстве",
        "промышленности",
        "ватс",
        "итс",
        "адаптивного обучения",
        "умный город",
        "iot",
    ],

    # 5. Отрасли
    "it": [
        "искусственный интеллект",
        "цифров",
        "информационн",
        "персональные данные",
        "данных",
        "информационные технологии",
        "минцифры",
        "машинное обучение",
        "нейрон",
        "программ",
    ],
    "transport": [
        "транспорт",
        "минтранс",
        "беспилот",
        "бпла",
        "бас",
        "дрон",
        "высокоавтоматизирован",
        "авиацион",
        "росавиац",
        "логистик",
        "ватс",
    ],
    "agriculture": [
        "сельскохоз",
        "сельское хозяйство",
        "минсельхоз",
        "агропромышлен",
        "апк",
        "растениевод",
        "животновод",
        "рыбохозяйствен",
    ],
}


def _to_text(value: Any) -> str:
    """Безопасно превращает любое значение в строку."""
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.extend(str(v) for v in item.values() if v is not None)
            else:
                parts.append(str(item))
        return " ".join(parts)

    if isinstance(value, dict):
        return " ".join(str(v) for v in value.values() if v is not None)

    return str(value)


def classify_document(
    doc_or_title: Any,
    summary: str = "",
    authority: str = "",
    doc_type: str = "",
) -> list[str]:
    """
    Классифицирует документ по ключевым словам.

    Поддерживает два варианта вызова:

    1. classify_document("Название документа")
    2. classify_document(document_dict)
    """

    if isinstance(doc_or_title, dict):
        doc = doc_or_title

        text_parts = [
            _to_text(doc.get("title")),
            _to_text(doc.get("short_title")),
            _to_text(doc.get("summary")),
            _to_text(doc.get("authority")),
            _to_text(doc.get("type")),
            _to_text(doc.get("doc_type")),
            _to_text(doc.get("number")),
            _to_text(doc.get("tags")),
            _to_text(doc.get("categories")),
        ]
    else:
        text_parts = [
            _to_text(doc_or_title),
            _to_text(summary),
            _to_text(authority),
            _to_text(doc_type),
        ]

    text = " ".join(part for part in text_parts if part).lower()

    matched: list[str] = []

    for category_slug, keywords in RULES.items():
        if any(keyword.lower() in text for keyword in keywords):
            matched.append(category_slug)

    # Дополнительная связка:
    # если документ относится к ГОСТам, он всегда попадает в общий уровень стандартизации.
    if any(slug in matched for slug in ["base-ai-gost", "data-gost", "industry-gost"]):
        if "standardization" not in matched:
            matched.append("standardization")

    # Если документ явно про ИИ, он должен быть в IT-контуре.
    if "искусственный интеллект" in text or " ии " in f" {text} ":
        if "it" not in matched:
            matched.append("it")

    return matched or ["it"]