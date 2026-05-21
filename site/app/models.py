from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


document_category = Table(
    "document_category",
    Base.metadata,
    Column("document_id", String(200), ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    example: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    parent_slug: Mapped[str | None] = mapped_column(String(80), nullable=True)

    documents: Mapped[list["Document"]] = relationship(
        secondary=document_category,
        back_populates="categories",
    )


class Document(Base):
    __tablename__ = "documents"

    # ВАЖНО: id строковый, потому что у нас pravo-..., digital-...
    id: Mapped[str] = mapped_column(String(200), primary_key=True)

    title: Mapped[str] = mapped_column(Text, index=True)
    short_title: Mapped[str | None] = mapped_column(Text, nullable=True)

    doc_type: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)
    number: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)

    # Пока храним даты строками, потому что из разных парсеров приходят разные форматы.
    date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    adopted_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    published_at: Mapped[str | None] = mapped_column(String(50), nullable=True)

    authority: Mapped[str | None] = mapped_column(String(300), index=True, nullable=True)
    status: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1000), unique=True, nullable=True)

    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    parser: Mapped[str | None] = mapped_column(String(150), index=True, nullable=True)

    is_parsed: Mapped[bool] = mapped_column(Boolean, default=True)
    is_downloaded: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    categories: Mapped[list[Category]] = relationship(
        secondary=document_category,
        back_populates="documents",
    )


class ParserRun(Base):
    __tablename__ = "parser_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    parser_name: Mapped[str] = mapped_column(String(150), index=True)
    source: Mapped[str | None] = mapped_column(String(150), nullable=True)
    found_count: Mapped[int] = mapped_column(default=0)
    added_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(50), default="success")
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)