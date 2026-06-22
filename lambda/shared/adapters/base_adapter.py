from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
import json
import logging
from typing import List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from shared.models import CanonicalRecallRecord
from shared.state_parsing import parse_distribution_pattern

logger = logging.getLogger(__name__)


class BaseRecallAdapter(ABC):
    SOURCE_NAME = ""
    CATEGORY = ""
    API_BASE_URL = ""

    @abstractmethod
    def fetch_raw_records(self, since_date: str = None, limit: int = 100) -> List[dict]:
        pass

    @abstractmethod
    def normalize(self, raw_record: dict) -> CanonicalRecallRecord:
        pass

    def ingest(self, since_date: str = None, limit: int = 100) -> List[CanonicalRecallRecord]:
        logger.info("[%s] Starting ingestion since=%s limit=%s", self.SOURCE_NAME, since_date, limit)
        raw_records = self.fetch_raw_records(since_date=since_date, limit=limit)
        normalized = []
        errors = 0

        for raw in raw_records:
            try:
                normalized.append(self.normalize(raw))
            except Exception as exc:
                errors += 1
                logger.error("[%s] Normalization error: %s", self.SOURCE_NAME, exc, exc_info=True)

        logger.info("[%s] Normalized %s records (%s errors)", self.SOURCE_NAME, len(normalized), errors)
        return normalized

    def get_json(self, params: dict = None, timeout: int = 30):
        url = self.API_BASE_URL
        if params:
            url = f"{url}?{urlencode(params)}"

        request = Request(url, headers={"Accept": "application/json", "User-Agent": "RecallRadar/3.0"})
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            logger.error("[%s] HTTP error: %s %s", self.SOURCE_NAME, exc.code, exc.reason)
        except URLError as exc:
            logger.error("[%s] Connection error: %s", self.SOURCE_NAME, exc.reason)
        except json.JSONDecodeError as exc:
            logger.error("[%s] Invalid JSON response: %s", self.SOURCE_NAME, exc)
        return [] if params is not None else {}

    def parse_states(self, distribution_text: str) -> list:
        parsed = parse_distribution_pattern(distribution_text or "")
        if parsed["is_nationwide"]:
            return ["Nationwide"]
        return parsed["affected_states"] or ["Unknown"]

    def default_since_date(self, days: int = 90) -> str:
        return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")

    def yyyymmdd(self, date_str: str) -> str:
        return (date_str or "").replace("-", "")[:8]

    def iso_from_yyyymmdd(self, date_str: str) -> str:
        cleaned = (date_str or "").strip()
        if len(cleaned) >= 8:
            return f"{cleaned[:4]}-{cleaned[4:6]}-{cleaned[6:8]}"
        return ""
