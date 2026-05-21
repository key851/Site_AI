from app.core.categories import CATEGORIES
from app.database import SessionLocal, init_db
from app.models import Category


def seed_categories() -> None:
    db = SessionLocal()

    try:
        for item in CATEGORIES:
            slug = item["slug"]

            category = db.query(Category).filter(Category.slug == slug).first()

            if not category:
                category = Category(slug=slug)
                db.add(category)

            category.title = item.get("title", slug)
            category.number = item.get("number") or None
            category.description = item.get("description") or None
            category.example = item.get("example") or None
            category.color = item.get("color") or None
            category.parent_slug = item.get("parent_slug") or None

        db.commit()
        print(f"[init_db] Категории добавлены/обновлены: {len(CATEGORIES)}")

    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_categories()
    print("[init_db] База данных готова")