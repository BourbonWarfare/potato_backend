import math
from typing import Any

import sqlalchemy
from sqlalchemy import select

from bw.models.arma import ArmaEvent
from bw.state import State


class ArmaEventStore:
    def create_event(self, state: State, tag: str, message: str) -> ArmaEvent:
        with state.Session.begin() as session:
            event = ArmaEvent(tag=tag, message=message)
            session.add(event)
            session.flush()
            session.refresh(event)
            session.expunge(event)
        return event

    def get_events_paginated(
        self, state: State, page: int = 1, page_size: int = 50, tags: list[str] | None = None
    ) -> dict[str, Any]:
        page = max(1, page)
        page_size = max(1, min(page_size, 500))
        tags = [tag for tag in tags or [] if tag]

        with state.Session.begin() as session:
            count_query = select(sqlalchemy.func.count()).select_from(ArmaEvent)
            events_query = select(ArmaEvent)
            if tags:
                count_query = count_query.where(ArmaEvent.tag.in_(tags))
                events_query = events_query.where(ArmaEvent.tag.in_(tags))

            total = session.scalar(count_query) or 0
            events = (
                session.execute(
                    events_query.order_by(ArmaEvent.creation_date.desc(), ArmaEvent.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
                .scalars()
                .all()
            )
            event_data = [event.to_json() for event in events]

        return {
            'events': event_data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': math.ceil(total / page_size) if total else 0,
            'tags': tags,
        }
