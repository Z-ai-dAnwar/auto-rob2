from dataclasses import dataclass, field


VALID_RESPONSE_OPTIONS = ("Y", "PY", "PN", "N", "NI", "NA")


@dataclass(frozen=True)
class Citation:
    label: str
    location: str

    def format(self) -> str:
        return f"{self.label} {self.location}".strip()


@dataclass(frozen=True)
class ResponseRule:
    guidance: str


@dataclass(frozen=True)
class RuleCard:
    sq_id: str
    question: str
    response_rules: dict[str, ResponseRule]
    citations: list[Citation]
    applicability: str = ""
    algorithm_note: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DomainMethodology:
    domain_id: str
    title: str
    principles: list[str]
    rule_cards: dict[str, RuleCard]
    citations: list[Citation] = field(default_factory=list)
