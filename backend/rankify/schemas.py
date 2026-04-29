from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    display_order: int


class CategoryListItem(BaseModel):
    id: int
    slug: str
    name: str
    item_count: int


class CategoryDetail(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None
    submission_count: int
    items: list[ItemOut]


class RankingSubmitRequest(BaseModel):
    category_id: int
    ordered_item_ids: list[int] = Field(min_length=1)
    anon_id: str | None = Field(default=None, max_length=80)

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
    total_submissions: int
    items: list[CommunityRankingItem]
