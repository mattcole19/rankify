from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

SLUG_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    display_order: int


class CategoryListItem(BaseModel):
    id: int
    slug: str
    name: str
    version_number: int
    item_count: int


class CategoryDetail(BaseModel):
    id: int
    slug: str
    name: str
    version_number: int
    description: str | None
    submission_count: int
    items: list[ItemOut]


class RankingSubmitRequest(BaseModel):
    category_id: int
    ordered_item_ids: list[int] = Field(min_length=1)
    anon_id: str = Field(min_length=1, max_length=80)

    @field_validator('ordered_item_ids')
    @classmethod
    def _must_be_unique(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError('ordered_item_ids must not contain duplicates')
        return value


class RankingSubmitResponse(BaseModel):
    submission_id: int
    anon_id: str


class CommunityRankingItem(BaseModel):
    item_id: int
    item_name: str
    average_rank: float | None
    vote_count: int


class CommunityRankingResponse(BaseModel):
    category_id: int
    category_slug: str
    category_version_number: int
    total_submissions: int
    items: list[CommunityRankingItem]


class CategoryVersionSummary(BaseModel):
    category_id: int
    version_number: int
    status: str
    item_count: int
    submission_count: int


class AdminCreateCategoryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2_000)

    @field_validator('name', 'slug', mode='before')
    @classmethod
    def _trim_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator('slug')
    @classmethod
    def _validate_slug_format(cls, value: str) -> str:
        if not SLUG_PATTERN.fullmatch(value):
            raise ValueError('slug must be lowercase letters, numbers, and dashes only')
        return value


class AdminCategoryResponse(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None
    version_number: int
    status: str


class AdminAddCategoryItemsRequest(BaseModel):
    items: list[str] = Field(min_length=1, max_length=200)

    @field_validator('items')
    @classmethod
    def _validate_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError('item names must not be empty')
        if len({item.lower() for item in cleaned}) != len(cleaned):
            raise ValueError('item names must be unique within the request')
        return cleaned


class AdminCreateCategoryVersionRequest(BaseModel):
    new_items: list[str] = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)

    @field_validator('new_items')
    @classmethod
    def _validate_new_items(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item for item in cleaned):
            raise ValueError('item names must not be empty')
        if len({item.lower() for item in cleaned}) != len(cleaned):
            raise ValueError('item names must be unique within the request')
        return cleaned
