OFFICIAL_SOURCES = [
    {
        "group": "Базовые источники",
        "items": [
            {
                "name": "Официальный интернет-портал правовой информации",
                "url": "http://publication.pravo.gov.ru/",
                "description": "Первая официальная публикация федеральных законов, указов Президента РФ, постановлений Правительства РФ и приказов федеральных органов исполнительной власти.",
                "status": "API доступен",
                "priority": "основной",
            },
            {
                "name": "Федеральный портал проектов нормативных правовых актов",
                "url": "https://regulation.gov.ru/",
                "description": "Источник проектов НПА до их принятия. Используется для мониторинга будущего регулирования ИИ.",
                "status": "RSS / CSV / HTML",
                "priority": "дополнительный",
            },
            {
                "name": "Система обеспечения законодательной деятельности",
                "url": "https://sozd.duma.gov.ru/",
                "description": "Законопроекты на стадиях рассмотрения в Государственной Думе.",
                "status": "API / RSS",
                "priority": "дополнительный",
            },
        ],
    },
    {
        "group": "ИТ и цифровая экономика",
        "items": [
            {
                "name": "Минцифры России",
                "url": "https://digital.gov.ru/documents",
                "description": "Документы по цифровой экономике, ИИ, данным, связи и информационным технологиям.",
                "status": "HTML / через pravo.gov.ru",
                "priority": "отраслевой",
            },
            {
                "name": "Минэкономразвития России",
                "url": "https://www.economy.gov.ru/material/dokumenty/",
                "description": "Документы по регулированию цифровой среды, экспериментальным правовым режимам и федеральному проекту «Искусственный интеллект».",
                "status": "HTML / через pravo.gov.ru",
                "priority": "отраслевой",
            },
        ],
    },
    {
        "group": "Транспорт и БПЛА",
        "items": [
            {
                "name": "Минтранс России",
                "url": "https://mintrans.gov.ru/documents",
                "description": "Документы по транспортной отрасли, высокоавтоматизированным транспортным средствам и беспилотным системам.",
                "status": "HTML / через pravo.gov.ru",
                "priority": "отраслевой",
            },
            {
                "name": "Публикации Минтранса на pravo.gov.ru",
                "url": "http://publication.pravo.gov.ru/documents/block/foiv275",
                "description": "Официальные публикации документов Минтранса.",
                "status": "официальная публикация",
                "priority": "основной",
            },
            {
                "name": "Росавиация",
                "url": "https://favt.gov.ru/o-rosaviacii-dokumenty/",
                "description": "Документы по БАС, БПЛА, авиационным правилам и сертификации.",
                "status": "HTML",
                "priority": "отраслевой",
            },
        ],
    },
    {
        "group": "Сельское хозяйство и АПК",
        "items": [
            {
                "name": "Минсельхоз России",
                "url": "https://mcx.gov.ru/docs/",
                "description": "Нормативные документы, госпрограммы и акты в сфере сельского хозяйства.",
                "status": "HTML / через pravo.gov.ru",
                "priority": "отраслевой",
            },
            {
                "name": "Публикации Минсельхоза на pravo.gov.ru",
                "url": "http://publication.pravo.gov.ru/documents/block/foiv266",
                "description": "Официальные публикации документов Минсельхоза.",
                "status": "официальная публикация",
                "priority": "основной",
            },
        ],
    },
    {
        "group": "ГОСТы по ИИ",
        "items": [
            {
                "name": "protect.gost.ru",
                "url": "https://protect.gost.ru/",
                "description": "Каталог стандартов. Используется для мониторинга ГОСТов и ПНСТ.",
                "status": "HTML / часть файлов требует авторизации",
                "priority": "основной",
            },
            {
                "name": "Стандарты ИИ на сайте Росстандарта",
                "url": "https://rst.gov.ru/portal/gost/home/standarts/aistandarts",
                "description": "Курируемый перечень стандартов по направлению «Искусственный интеллект».",
                "status": "HTML",
                "priority": "основной",
            },
        ],
    },
]