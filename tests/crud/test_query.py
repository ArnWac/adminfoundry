"""Tests for CRUD query helpers."""

from __future__ import annotations

import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

from adminfoundry.crud.query import (
    apply_ordering,
    apply_search,
    coerce_primary_key_value,
    normalize_limit_offset,
    primary_key_column,
)
from adminfoundry.registry import ModelAdmin


class _Base(DeclarativeBase):
    pass


class Product(_Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    sku = Column(String(50))


class ProductAdmin(ModelAdmin):
    model = Product
    search_fields = ["name", "sku"]
    ordering = ["name"]


# --- normalize_limit_offset ---


def test_normalize_limit_clamps_to_max():
    limit, offset = normalize_limit_offset(limit=9999, offset=0)
    assert limit <= 500


def test_normalize_offset_clamps_to_zero():
    _, offset = normalize_limit_offset(limit=10, offset=-5)
    assert offset == 0


# --- primary_key_column ---


def test_primary_key_column_found():
    col = primary_key_column(Product)
    assert col.name == "id"


# --- coerce_primary_key_value ---


def test_coerce_int_pk():
    val = coerce_primary_key_value(Product, "42")
    assert val == 42


def test_coerce_invalid_int_raises_422():
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        coerce_primary_key_value(Product, "not-an-int")


# --- apply_search ---


def test_apply_search_no_term_is_noop():
    from sqlalchemy import select

    stmt = select(Product)
    result = apply_search(stmt, ProductAdmin(), None)
    assert str(result) == str(stmt)


def test_apply_search_adds_where():
    from sqlalchemy import select

    stmt = select(Product)
    result = apply_search(stmt, ProductAdmin(), "test")
    assert "WHERE" in str(result).upper()


# --- apply_ordering ---


def test_apply_ordering_uses_admin_ordering():
    from sqlalchemy import select

    stmt = select(Product)
    result = apply_ordering(stmt, ProductAdmin())
    assert "ORDER BY" in str(result).upper()
