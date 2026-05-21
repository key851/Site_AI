from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedDocument:
    title: str
    source_url: str
    source_name: str
    type: str = "НПА"
    number: str = ""
    date: str = ""
    authority: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "source_url": self.source_url,
            "source_name": self.source_name,
            "type": self.type,
            "number": self.number,
            "date": self.date,
            "authority": self.authority,
            "summary": self.summary,
            "tags": self.tags,
            "categories": self.categories,
        }
