import os
import sqlite3
import logging
import json
from supabase import Client, create_client
from prisma import Prisma
from typing import Dict, Any, Optional
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def store_analysis_data(data: Dict[str, Any]) -> None:
    """Store analysis data using Prisma with JSON serialization"""
    db = Prisma()
    await db.connect()

    try:
        await db.analysis.create(
            data={
                "repoUrl": data["url"],
                "repoName": data.get("repo_name"),
                "repoOwner": data.get("repo_owner"),
                "repoBranch": data.get("repo_branch"),
                "repoCommitSha": data.get("repo_commit_sha"),
                "isPrivate": data.get("is_private", False),
                "userId": data["user_id"],
            }
        )
    finally:
        await db.disconnect()


def parse_json_field(field: Optional[str], field_name: str) -> Any:
    """Safely parse a JSON field from the database"""
    if field is None:
        raise HTTPException(
            status_code=500, detail=f"Database error: {field_name} field is None"
        )
    try:
        return json.loads(field)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail=f"Database error: Invalid JSON in {field_name}"
        )
