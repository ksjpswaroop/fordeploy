from app.schemas.common import PaginationMeta


def build_pagination_meta(total: int, skip: int, limit: int) -> PaginationMeta:
    page = (skip // limit) + 1 if limit else 1
    total_pages = (total + limit - 1) // limit if limit else 1
    has_next = skip + limit < total
    has_prev = skip > 0
    return PaginationMeta(
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
    )
