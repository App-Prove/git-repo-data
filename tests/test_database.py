import pytest
import json
from prisma import Prisma
from prisma.models import Analysis


@pytest.fixture
async def db():
    """Database fixture"""
    db = Prisma()
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def test_user(db):
    """Create a test user"""
    user = await db.user.create({})
    yield user
    await db.user.delete(where={"id": user.id})


@pytest.mark.asyncio
async def test_store_analysis_data(db, test_user):
    """Test storing basic analysis data"""
    analysis = await db.analysis.create(
        data={
            "userId": test_user.id,
            "repoUrl": "https://github.com/test/repo",
            "repoName": "test",
            "repoOwner": "test-owner",
            "repoBranch": "main",
            "repoCommitSha": "abc123",
            "isPrivate": False,
        }
    )

    try:
        assert analysis.repoUrl == "https://github.com/test/repo"
        assert analysis.repoName == "test"
        assert analysis.repoOwner == "test-owner"
        assert analysis.repoBranch == "main"
        assert analysis.repoCommitSha == "abc123"
        assert analysis.isPrivate is False
    finally:
        await db.analysis.delete(where={"id": analysis.id})


@pytest.mark.asyncio
async def test_store_file_tree(db, test_user):
    """Test storing file tree data with parent-child relationships"""
    analysis = await db.analysis.create(
        data={
            "userId": test_user.id,
            "repoUrl": "https://github.com/test/repo",
        }
    )

    try:
        # Create root directory
        root_dir = await db.filetree.create(
            data={
                "name": "root",
                "type": "directory",
                "analysisId": analysis.id,
            }
        )

        # Create subdirectory
        sub_dir = await db.filetree.create(
            data={
                "name": "src",
                "type": "directory",
                "path": "src",
                "analysisId": analysis.id,
                "parentId": root_dir.id,
            }
        )

        # Create file in subdirectory
        file = await db.filetree.create(
            data={
                "name": "main.py",
                "type": "file",
                "path": "src/main.py",
                "content": "print('hello')",
                "analysisId": analysis.id,
                "parentId": sub_dir.id,
            }
        )

        # Verify the structure
        assert root_dir.name == "root"
        assert root_dir.type == "directory"
        assert sub_dir.parentId == root_dir.id
        assert file.parentId == sub_dir.id
        assert file.content == "print('hello')"

    finally:
        await db.analysis.delete(where={"id": analysis.id})


@pytest.mark.asyncio
async def test_store_issues(db, test_user):
    """Test storing security issues"""
    analysis = await db.analysis.create(
        data={
            "userId": test_user.id,
            "repoUrl": "https://github.com/test/repo",
        }
    )

    try:
        # Create test issue
        issue = await db.issue.create(
            data={
                "title": "Security Vulnerability",
                "description": "Hardcoded credentials found",
                "severity": "HIGH",
                "filePath": "config.py",
                "lineNumber": 42,
                "analysisId": analysis.id,
            }
        )

        # Verify the issue
        assert issue.title == "Security Vulnerability"
        assert issue.severity == "HIGH"
        assert issue.lineNumber == 42
        assert issue.filePath == "config.py"

        # Test retrieving issues for analysis
        issues = await db.issue.find_many(
            where={"analysisId": analysis.id}
        )
        assert len(issues) == 1
        assert issues[0].id == issue.id

    finally:
        await db.analysis.delete(where={"id": analysis.id})


@pytest.mark.asyncio
async def test_analysis_relationships(db, test_user):
    """Test relationships between Analysis, FileTree, and Issues"""
    analysis = await db.analysis.create(
        data={
            "userId": test_user.id,
            "repoUrl": "https://github.com/test/repo",
        }
    )

    try:
        # Create file tree
        file_tree = await db.filetree.create(
            data={
                "name": "root",
                "type": "directory",
                "analysisId": analysis.id,
            }
        )

        # Create issue
        issue = await db.issue.create(
            data={
                "title": "Test Issue",
                "description": "Test Description",
                "severity": "LOW",
                "analysisId": analysis.id,
            }
        )

        # Fetch analysis with relationships
        full_analysis = await db.analysis.find_unique(
            where={"id": analysis.id},
            include={
                "fileTree": True,
                "issues": True,
                "user": True,
            }
        )

        # Verify relationships
        assert full_analysis.fileTree.id == file_tree.id
        assert len(full_analysis.issues) == 1
        assert full_analysis.issues[0].id == issue.id
        assert full_analysis.user.id == test_user.id

    finally:
        await db.analysis.delete(where={"id": analysis.id})


@pytest.mark.asyncio
async def test_error_handling(db, test_user):
    """Test error cases for database operations"""
    
    # Test duplicate FileTree for analysis
    analysis = await db.analysis.create(
        data={
            "userId": test_user.id,
            "repoUrl": "https://github.com/test/repo",
        }
    )

    try:
        # Create first file tree
        await db.filetree.create(
            data={
                "name": "root1",
                "type": "directory",
                "analysisId": analysis.id,
            }
        )

        # Attempt to create second file tree (should fail due to unique constraint)
        with pytest.raises(Exception):
            await db.filetree.create(
                data={
                    "name": "root2",
                    "type": "directory",
                    "analysisId": analysis.id,
                }
            )

    finally:
        await db.analysis.delete(where={"id": analysis.id})

    # Test invalid relationships
    with pytest.raises(Exception):
        await db.analysis.create(
            data={
                "userId": "invalid-user-id",  # Non-existent user ID
                "repoUrl": "https://github.com/test/repo",
            }
        )

    # Test required fields
    with pytest.raises(Exception):
        await db.issue.create(
            data={
                "title": "Missing Required Fields",
                # Missing required fields: description, severity, analysisId
            }
        )
