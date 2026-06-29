"""Shared base models and utilities."""

import uuid
from typing import Any

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract model with created_at and updated_at timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet[Any]):
    """QuerySet that filters out soft-deleted records by default."""

    def delete(self) -> tuple[int, dict[str, int]]:
        count = self.update(deleted_at=timezone.now())
        return count, {self.model._meta.label: count}

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        return super().delete()

    def alive(self) -> models.QuerySet[Any]:
        return self.filter(deleted_at__isnull=True)

    def dead(self) -> models.QuerySet[Any]:
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager[Any]):
    """Manager that excludes soft-deleted records."""

    def get_queryset(self) -> models.QuerySet[Any]:
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(TimeStampedModel):
    """Abstract model with soft delete support via deleted_at."""

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects: SoftDeleteManager = SoftDeleteManager()
    all_objects: models.Manager[Any] = models.Manager()

    class Meta:
        abstract = True

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])
        return 1, {self._meta.label: 1}

    def hard_delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        return super().delete(using=using, keep_parents=keep_parents)


class UUIDModel(models.Model):
    """Abstract model with UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, SoftDeleteModel):
    """Base model combining UUID primary key, timestamps, and soft delete."""

    class Meta:
        abstract = True


class DomainModel(UUIDModel, TimeStampedModel):
    """Base model for domain entities with UUID primary key and timestamps."""

    class Meta:
        abstract = True
