__all__ = ["helper"]

from datetime import datetime, timezone

from flask import g, has_request_context, request

from app.core.logging import get_logger

logger = get_logger()


class HelperFunctions:
    @staticmethod
    def build_paginated_response(items, limit, offset, total):
        """
        :param items: The items to send
        :param limit: The limit set for the items
        :param offset: The offset of the query
        :param total: Total amount of items in database
        :return: Dictionary to return
        """
        return {"items": items, "limit": limit, "offset": offset, "total": total}

    def get_request_context(self) -> dict:
        """
        :return: Context dictionary of request
        """
        if not has_request_context():
            return {}

        context = {
            "method": request.method,
            "path": request.path,
            "endpoint": request.endpoint,
            "ip": request.remote_addr,
        }

        if hasattr(g, "user_id"):
            context["user_id"] = g.user_id

        return context


helper = HelperFunctions()


def ensure_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
