"""Единая структура категорий сайта.

Пока БД нет, дерево категорий живёт здесь. Потом эти данные можно перенести
в таблицу categories, а slug/code оставить такими же, чтобы не ломать ссылки.
"""

CATEGORY_TREE = [
    {
        "slug": "strategy",
        "number": "1",
        "title": "Стратегический и концептуальный уровень",
        "color": "blue",
        "description": "Стратегия ИИ, цифровая политика, концепции и мягкое регулирование.",
        "children": [
            {"slug": "state-ai-strategy", "title": "Государственная стратегия развития ИИ", "example": "Указ Президента РФ № 490; Указ № 124"},
            {"slug": "digital-policy", "title": "Общая цифровая политика государства", "example": "нацпрограмма «Цифровая экономика РФ»; нацпроект «Экономика данных»"},
            {"slug": "ai-legal-concept", "title": "Концепция правового регулирования ИИ", "example": "распоряжение Правительства РФ № 2129-р"},
            {"slug": "soft-law", "title": "Мягкое регулирование", "example": "Кодекс этики в сфере ИИ"},
        ],
    },
    {
        "slug": "legislation",
        "number": "2",
        "title": "Законодательный уровень",
        "color": "green",
        "description": "Базовые законы, экспериментальные режимы и законопроектные инициативы.",
        "children": [
            {"slug": "base-laws", "title": "Базовые законы для ИИ", "example": "149-ФЗ, 152-ФЗ, 187-ФЗ, ГК РФ ч. IV"},
            {"slug": "experimental-regulation", "title": "Экспериментальное регулирование", "example": "258-ФЗ, ПП РФ № 1750, 123-ФЗ"},
            {"slug": "legislative-initiatives", "title": "Законодательные инициативы", "example": "проект ФЗ о регулировании применения ИИ"},
        ],
    },
    {
        "slug": "support",
        "number": "3",
        "title": "Государственная поддержка и внедрение",
        "color": "orange",
        "description": "Гранты, исследовательские центры, критерии ИИ-проектов и внедрение.",
        "children": [
            {"slug": "financial-support", "title": "Финансовая поддержка", "example": "Постановление Правительства РФ № 456"},
            {"slug": "research-support", "title": "Исследовательская поддержка", "example": "Постановление Правительства РФ № 1120"},
            {"slug": "ai-project-criteria", "title": "Критерии ИИ-проектов", "example": "Приказ Минэкономразвития РФ № 392"},
        ],
    },
    {
        "slug": "standardization",
        "number": "4",
        "title": "Уровень стандартизации",
        "color": "purple",
        "description": "ГОСТы и ПНСТ: терминология, данные, качество, доверие и отраслевые стандарты.",
        "children": [
            {"slug": "base-ai-gost", "title": "Базовые ГОСТы по ИИ", "example": "ГОСТ Р 71476-2024; ГОСТ Р 59277-2020"},
            {"slug": "data-gost", "title": "ГОСТы по данным", "example": "ГОСТ Р 71484.1-2024; ГОСТ Р 71484.2-2024"},
            {"slug": "trust-security-gost", "title": "ГОСТы по безопасности и доверию", "example": "ГОСТ Р 59276-2020; ГОСТ Р 59898-2021"},
            {
                "slug": "industry-gost",
                "title": "Отраслевые ГОСТы",
                "example": "медицина, АПК, транспорт, промышленность",
                "children": [
                    {"slug": "it-gost", "title": "IT / ИИ", "example": "ГОСТ Р 71476-2024"},
                    {"slug": "transport-gost", "title": "Транспорт и БПЛА", "example": "серия ГОСТ Р ВАТС и ИТС"},
                    {"slug": "agriculture-gost", "title": "Сельское хозяйство", "example": "ГОСТ Р 59920-2021"},
                ],
            },
        ],
    },
    {
        "slug": "industries",
        "number": "5",
        "title": "Отраслевые контуры регулирования и применения ИИ",
        "color": "teal",
        "description": "Рабочие отрасли проекта: IT, транспорт/БПЛА и сельское хозяйство. Остальное — заглушки.",
        "children": [
            {"slug": "it", "title": "IT и цифровая экономика", "example": "149-ФЗ; нацпроект «Экономика данных»"},
            {"slug": "transport", "title": "Транспорт и беспилотные системы", "example": "ПП РФ № 309; документы Минтранса и Росавиации"},
            {"slug": "agriculture", "title": "Сельское хозяйство и АПК", "example": "расп. Правительства РФ № 3309-р; документы Минсельхоза"},
            {"slug": "healthcare-stub", "title": "Здравоохранение", "example": "заглушка"},
            {"slug": "finance-stub", "title": "Финансовый сектор", "example": "заглушка"},
            {"slug": "education-stub", "title": "Наука и образование", "example": "заглушка"},
        ],
    },
]


def flatten_categories(tree=None, parent_slug=None):
    """Плоский список категорий для фильтров и поиска."""
    tree = tree or CATEGORY_TREE
    result = []
    for node in tree:
        row = {
            "slug": node["slug"],
            "title": node["title"],
            "number": node.get("number", ""),
            "color": node.get("color", ""),
            "description": node.get("description", ""),
            "example": node.get("example", ""),
            "parent_slug": parent_slug,
        }
        result.append(row)
        if node.get("children"):
            result.extend(flatten_categories(node["children"], node["slug"]))
    return result


CATEGORIES = flatten_categories()
CATEGORY_BY_SLUG = {category["slug"]: category for category in CATEGORIES}
