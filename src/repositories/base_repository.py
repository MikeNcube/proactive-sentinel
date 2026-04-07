from typing import Any, Generic, Optional, TypeVar

from flask import g, has_request_context, request
from sqlalchemy.orm import Query

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository with tenant-aware CRUD helpers."""

    def __init__(self, model: type[T], db: Any):
        self.model = model
        self.db = db

    def _apply_tenant_filter(self, query: Query) -> Query:
        """Automatically apply tenant filter to all queries."""
        if hasattr(self.model, "tenant_id"):
            tenant_id = getattr(g, "tenant_id", None)
            if not tenant_id and has_request_context():
                tenant_id = request.headers.get("X-Tenant-ID")
            if tenant_id:
                return query.filter(self.model.tenant_id == tenant_id)
        return query

    def get_by_id(self, id: Any) -> Optional[T]:
        query = self.model.query.filter_by(id=id)
        query = self._apply_tenant_filter(query)
        return query.first()

    def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        query = self.model.query
        query = self._apply_tenant_filter(query)
        return query.limit(limit).offset(offset).all()

    def create(self, **kwargs: Any) -> T:
        # Auto-populate tenant_id if model has it
        if hasattr(self.model, "tenant_id") and "tenant_id" not in kwargs:
            if hasattr(g, "tenant_id"):
                kwargs["tenant_id"] = g.tenant_id

        instance = self.model(**kwargs)  # type: ignore[call-arg]
        try:
            self.db.session.add(instance)
            self.db.session.commit()
            return instance
        except Exception:
            self.db.session.rollback()
            raise

    def update(self, id: Any, **kwargs: Any) -> Optional[T]:
        instance = self.get_by_id(id)
        if instance:
            try:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                self.db.session.commit()
            except Exception:
                self.db.session.rollback()
                raise
        return instance

    def delete(self, id: Any) -> bool:
        instance = self.get_by_id(id)
        if instance:
            try:
                self.db.session.delete(instance)
                self.db.session.commit()
                return True
            except Exception:
                self.db.session.rollback()
                raise
        return False
