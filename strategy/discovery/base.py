from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class KeywordCandidate:
    keyword: str
    source: str
    page_source: str = ''
    confidence: float = 0.5
    notes: str = ''


class Collector(ABC):
    name = 'base'

    @abstractmethod
    def collect(self, project) -> list:
        """Return a list[KeywordCandidate] from real data (no AI)."""
