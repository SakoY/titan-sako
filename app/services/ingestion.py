"""Catalog ingestion pipeline — single-work and batch orchestration."""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.repositories.work_repo import upsert_work
from app.services.ol_client import OLClient, OLClientError, build_cover_url

logger = logging.getLogger(__name__)

_PAGE_SIZE = 50
_MAX_WORKS = 500


async def ingest_single_work(
    db: Session,
    ol_client: OLClient,
    tenant_id: str,
    raw_work: dict,
) -> dict:
    """
    Resolve author names and cover URL for a single raw OL work dict, then upsert
    into the DB.

    Returns:
        {"status": "success", "ol_work_key": str}
        {"status": "failed",  "error": str}
    """
    ol_work_key = raw_work.get("key")
    try:
        # Resolve author names from author_key list
        author_names: list[str] = []
        for ak in raw_work.get("author_key") or []:
            try:
                author = await ol_client.get_author(ak)
                author_names.append(author["name"])
            except OLClientError as exc:
                logger.warning("Failed to resolve author %s: %s", ak, exc)
                author_names.append("Unknown")

        cover_image_url = build_cover_url(raw_work.get("cover_i"))

        work_data = {
            "key": ol_work_key,
            "title": raw_work.get("title"),
            "author_names": author_names,
            "first_publish_year": raw_work.get("first_publish_year"),
            "subjects": raw_work.get("subject") or [],
            "cover_image_url": cover_image_url,
        }

        upsert_work(db, tenant_id, work_data)
        return {"status": "success", "ol_work_key": ol_work_key}

    except Exception as exc:
        logger.error("Failed to ingest work %s: %s", ol_work_key, exc)
        return {"status": "failed", "error": str(exc)}


async def run_ingestion(
    db: Session,
    ol_client: OLClient,
    tenant_id: str,
    query_type: str,
    query_value: str,
    log_id: str,
) -> None:
    """
    Paginate through OL search results and ingest each work.
    Updates the IngestionLog row after each page. Marks the log
    completed or failed on exit.
    """
    from app.models.ingestion_log import IngestionLog

    log = db.query(IngestionLog).filter_by(id=log_id).one()
    log.status = "running"
    db.commit()

    fetched = 0
    succeeded = 0
    failed = 0
    offset = 0

    try:
        while fetched < _MAX_WORKS:
            limit = min(_PAGE_SIZE, _MAX_WORKS - fetched)

            if query_type == "author":
                works = await ol_client.search_works_by_author(query_value, limit=limit, offset=offset)
            else:
                works = await ol_client.search_works_by_subject(query_value, limit=limit, offset=offset)

            if not works:
                break

            for raw_work in works:
                result = await ingest_single_work(db, ol_client, tenant_id, raw_work)
                if result["status"] == "success":
                    succeeded += 1
                else:
                    failed += 1

            fetched += len(works)
            offset += len(works)

            # Update log after each page
            log.fetched_count = fetched
            log.succeeded_count = succeeded
            log.failed_count = failed
            db.commit()

            if len(works) < limit:
                break  # last page — OL returned fewer than requested

        log.status = "completed"

    except Exception as exc:
        logger.error("Ingestion run %s failed: %s", log_id, exc)
        log.status = "failed"
        log.error_details = str(exc)

    finally:
        log.fetched_count = fetched
        log.succeeded_count = succeeded
        log.failed_count = failed
        log.finished_at = datetime.now(timezone.utc)
        db.commit()
