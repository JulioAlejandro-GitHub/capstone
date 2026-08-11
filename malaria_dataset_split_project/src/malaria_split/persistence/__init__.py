"""PostgreSQL persistence primitives for governed dataset splits."""

from .database import create_postgresql_engine

__all__ = ["create_postgresql_engine"]
