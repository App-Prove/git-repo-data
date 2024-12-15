import json
import os
import logging
from fastapi import WebSocket
import pandas as pd
import chardet
from utils.websocket import WebSocketAPI

from pathlib import Path
from typing import List, Tuple, Dict, Optional
from collections import Counter
from .ml import OllamaApi
from git import Repo
from prisma import Prisma


logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# config_path = "app/utils/analysis/config/supported_extensions.csv"

logger.debug("Loading GPT Model")
model = OllamaApi()
logger.debug("Model loaded")


def get_important_programming_language(list_files: List[Path]) -> pd.DataFrame:
    """Returns programming languages detected in the files using Ollama model"""
    logger.debug("Detecting programming languages")

    # Create a list to store language detection results
    language_counts = Counter()

    for file_path in list_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Read first few lines of the file (enough for language detection)
                sample_content = "".join(f.readlines()[:20])

            # Ask Ollama to identify the programming language
            language = model.identify_programming_language(sample_content)

            if language:
                language_counts[language] += 1

        except Exception as error:
            logger.error(f"Error processing file {file_path}: {error}")
            continue

    # Convert to DataFrame
    df = pd.DataFrame(
        [(lang, count) for lang, count in language_counts.most_common()],
        columns=["name", "count"],
    )

    logger.debug(f"Detected languages: {df}")
    return df


def get_in_depth_file_analysis(
    *,
    list_files: List[dict[str, str]],
    audit_type: str = "security",
) -> List[dict[str, str]]:
    """Asynchronously analyse each file with GPT to locate sensitive code
    For each file it returns a list of issues which are dict with keys:
    - lineNumber
    - initialCode
    -
    - comment
    - suggestion

    We have to ensure we lead an analysis on relevent files (files that are likely to contain sensitive code)
    """
    in_depth_results = []
    # Limit the number of files to 5 for testing
    list_files = list_files[:5]
    for index, file_data in enumerate(list_files):
        logger.error(file_data)
        file_path = str(file_data.get("path"))
        try:
            with open(file_path, "r") as file:
                logger.info(f"Reading file : {file_path}")
                # Put line numbers before each line so GPT can understand the context
                content = list(
                    map(
                        lambda line: f"{line[0]}. {line[1]}" if line[1] != "" else None,
                        enumerate(file.readlines(), 1),
                    )
                )
                code = "".join([line for line in content if line is not None])
                logger.info(f"Code to analyze : {code}")
                in_depth_result = model.in_depth_analysis(
                    code, str(file_data.get("language")), audit_type
                )
                try:
                    # Try to format the data in json
                    in_depth_result = json.loads(in_depth_result)
                    # We should get something like {"issues":[]}
                except Exception as error:
                    logger.error(
                        f"When identifying in depth file analysis an error has occured (likely GPT forgetting issues key) : {error}"
                    )
                    continue  # Goes to next file
                logger.warning(f"Sensitive code found in file : {file_path}")
                logger.warning(in_depth_result)
                in_depth_result["path"] = file_path
                in_depth_results.append(in_depth_result)  # Add the analysis to the list
        except Exception as error:
            logger.error(f"An error has occured for file : {file_path} : {error}")
    return in_depth_results


def format_github_url(url: str) -> Tuple[str, str, str]:
    """
    Format the URL and extract repository information
    Returns: (formatted_url, owner, repo_name)
    """
    # Make sure there is github.com in the URL
    if "github.com" not in url:
        url = f"github.com/{url}"
    # Make sure there is https:// in the URL
    if "https://" not in url:
        url = f"https://{url}"
    
    # Extract owner and repo name from URL
    parts = url.split('github.com/')[-1].split('/')
    owner = parts[0]
    repo_name = parts[1] if len(parts) > 1 else ""
    
    return url, owner, repo_name


def clone_repo(repo_url, clone_dir):
    if not os.path.exists(clone_dir):
        os.makedirs(clone_dir)
    # Remove all files in the directory
    clean_dir(clone_dir)
    # Clone the repository
    Repo.clone_from(repo_url, clone_dir)


def clean_dir(clone_dir):
    # Remove all files in the directory
    for root, dirs, files in os.walk(clone_dir, topdown=False, followlinks=True):
        for file in files:
            logger.debug(f"Removing file {file}")
            os.remove(os.path.join(root, file))
        for dir in dirs:
            logger.debug(f"Removing dir {dir}")
            os.rmdir(os.path.join(root, dir))
    os.rmdir(clone_dir)


# Function to count lines in a file
def count_lines(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
            return len(lines)
    except UnicodeDecodeError as e:
        print(f"Decoding error for file {file_path}: {e}")
        return 0
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0


async def store_repository_analysis(
    analysis_id: str,
    number_of_files: int,
    total_line_count: int,
    programming_languages: pd.DataFrame,
    file_analysis: List[dict[str, str]],
    repo_url: str,
) -> None:
    """Store repository analysis results in the database"""
    db = Prisma()
    await db.connect()
    
    try:
        # Extract repository information
        formatted_url, repo_owner, repo_name = format_github_url(repo_url)
        
        # Update Analysis with repository information
        await db.analysis.update(
            where={"id": analysis_id},
            data={
                "repoUrl": formatted_url,
                "repoOwner": repo_owner,
                "repoName": repo_name,
                # You might want to add logic to get these values
                "repoBranch": "main",  # Default to main
                "repoCommitSha": None,  # Add logic to get current commit SHA
            }
        )

        # Store file tree
        for file_data in file_analysis:
            path_parts = Path(file_data["path"]).parts
            current_parent_id = None

            # Create directory structure
            for i, part in enumerate(path_parts[:-1]):
                current_path = str(Path(*path_parts[: i + 1]))
                
                # Check if directory already exists
                existing_dir = await db.filetree.find_first(
                    where={
                        "analysisId": analysis_id,
                        "path": current_path,
                        "type": "directory"
                    }
                )
                
                if existing_dir:
                    current_parent_id = existing_dir.id
                    continue

                # Create new directory
                directory = await db.filetree.create(
                    data={
                        "name": part,
                        "path": current_path,
                        "type": "directory",
                        "analysisId": analysis_id,
                        "parentId": current_parent_id,
                    }
                )
                current_parent_id = directory.id

            # Create file entry
            with open(file_data["path"], "r", encoding="utf-8") as f:
                content = f.read()

            await db.filetree.create(
                data={
                    "name": path_parts[-1],
                    "path": file_data["path"],
                    "type": "file",
                    "content": content,
                    "analysisId": analysis_id,
                    "parentId": current_parent_id,
                }
            )
    finally:
        await db.disconnect()


async def update_sensitive_files(
    analysis_id: str, 
    sensitive_files: dict
) -> None:
    """Create issues for sensitive files"""
    db = Prisma()
    await db.connect()
    
    try:
        for file_data in sensitive_files.get("sensitiveFiles", []):
            await db.issue.create(
                data={
                    "title": "Sensitive File Detected",
                    "description": f"Sensitive content found in {file_data['path']}",
                    "severity": "HIGH",
                    "filePath": file_data["path"],
                    "analysisId": analysis_id,
                }
            )
    finally:
        await db.disconnect()


async def get_sensitive_files(
    analysis_id: str,
    list_files: List[dict[str, str]]
) -> dict[str, List[dict[str, str]]]:
    """Identify and store sensitive files as issues"""
    db = Prisma()
    await db.connect()
    
    try:
        sensitive_files = model.identify_sensitive_files(list_files)
        sensitive_files_data = json.loads(str(sensitive_files))
        
        # Create issues for sensitive files
        await update_sensitive_files(analysis_id, sensitive_files_data)
        return sensitive_files_data
    except Exception as error:
        logger.error(f"Error identifying sensitive files: {error}")
        return {"sensitiveFiles": []}
    finally:
        await db.disconnect()


async def get_simple_repository_analysis(
    clone_dir: Path,
    analysis_id: str,
    repo_url: str,
) -> Tuple[int, int, List[str], List[dict]]:
    """Analyse the repository and store results"""
    if isinstance(clone_dir, str):
        clone_dir = Path(clone_dir)
        
    # Get repository information from git
    repo = Repo(clone_dir)
    try:
        commit_sha = repo.head.commit.hexsha
        branch = repo.active_branch.name
    except Exception as e:
        logger.error(f"Error getting git information: {e}")
        commit_sha = None
        branch = "main"

    list_files_paths = list(clone_dir.rglob("*.*"))
    number_of_files = len(list_files_paths)
    total_line_count = 0
    for file_path in list_files_paths:
        total_line_count += count_lines(file_path)

    important_programming_language = get_important_programming_language(
        list_files_paths
    )

    # Get list of detected programming languages
    list_of_programming_languages = important_programming_language["name"].to_list()

    # Create list of files with detected languages
    ready_for_analysis = []
    for file_path in list_files_paths:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                sample_content = "".join(f.readlines()[:20])
            language = model.identify_programming_language(sample_content)
            if language:
                ready_for_analysis.append(
                    {"path": str(file_path), "language": language}
                )
        except Exception as error:
            logger.error(f"Error processing file {file_path}: {error}")
            continue

    results = (
        number_of_files,
        total_line_count,
        list_of_programming_languages,
        ready_for_analysis,
    )

    # Store results in database
    await store_repository_analysis(
        analysis_id,
        number_of_files,
        total_line_count,
        important_programming_language,
        ready_for_analysis,
        repo_url,
    )

    # Update repository information
    db = Prisma()
    await db.connect()
    try:
        await db.analysis.update(
            where={"id": analysis_id},
            data={
                "repoBranch": branch,
                "repoCommitSha": commit_sha,
            }
        )
    finally:
        await db.disconnect()

    return results
