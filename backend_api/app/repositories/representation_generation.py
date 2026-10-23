"""REPRESENT HTTP catalog, on the same assessment transaction scope as EXPLAIN."""
from app.repositories.explain_generation import assessment_scope
from app.repositories.representation_queries import RepresentQueries


class RepresentRepository(RepresentQueries):
    def __init__(self) -> None:
        super().__init__(scope=assessment_scope)
