from app.parsers.digital_parser import fetch_digital_gov_documents
from app.parsers.pravo_parser import fetch_pravo_documents
from app.parsers.pravo_section_parser import fetch_ministry_section_documents
from app.services.db_document_service import add_parsed_documents
from app.parsers.gost_parser import fetch_gost_documents

#python -m app.scripts.run_big_parse 

def save_batch(name: str, documents: list[dict]) -> None:
    print()
    print("=" * 80)
    print(f"[big_parse] {name}: найдено парсером {len(documents)}")
    added = add_parsed_documents(documents)
    print(f"[big_parse] {name}: добавлено новых в БД {added}")
    print("=" * 80)
    print()


def main():
    print("[big_parse] Старт большого парсинга")

    # 1. Минтранс / БПЛА / транспорт
    mintrans_docs = fetch_ministry_section_documents(
        "transport",
        limit=2000,
        scan_limit=10000,
        page_size=200,
    )
    save_batch("Минтранс", mintrans_docs)

    # 2. Минсельхоз / АПК
    mcx_docs = fetch_ministry_section_documents(
        "agriculture",
        limit=2000,
        scan_limit=10000,
        page_size=200,
    )
    save_batch("Минсельхоз", mcx_docs)

    # 3. Минцифры
    digital_docs = fetch_digital_gov_documents(
        max_pages_per_query=50,
        max_catalog_pages=2000,
    )
    save_batch("Минцифры", digital_docs)

    gost_docs = fetch_gost_documents(download_pdfs=False)
    save_batch("ГОСТы Росстандарта", gost_docs)

    # 4. Общий мониторинг pravo.gov.ru
    pravo_docs = fetch_pravo_documents(
        days_back=3650,
        page_size=200,
    )
    save_batch("Общий pravo.gov.ru", pravo_docs)

    print("[big_parse] Готово")


if __name__ == "__main__":
    main()