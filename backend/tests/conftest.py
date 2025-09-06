import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import tempfile
import os
from typing import Dict, Any, List
import sys

# Add the backend directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    mock_config = Mock()
    mock_config.anthropic_api_key = "test_api_key"
    mock_config.model_name = "claude-3-sonnet-20241022"
    mock_config.chunk_size = 800
    mock_config.chunk_overlap = 100
    mock_config.embedding_model = "all-MiniLM-L6-v2"
    mock_config.chroma_path = "test_chroma_db"
    mock_config.max_search_results = 5
    mock_config.max_conversation_history = 10
    return mock_config

@pytest.fixture
def mock_rag_system():
    """Mock RAG system for API testing"""
    mock_rag = Mock()
    mock_rag.query.return_value = (
        "Test response", 
        [{"title": "Test Course", "url": "http://example.com"}]
    )
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Test Course 1", "Test Course 2"]
    }
    mock_rag.session_manager = Mock()
    mock_rag.session_manager.create_session.return_value = "test_session_123"
    mock_rag.session_manager.clear_session.return_value = None
    return mock_rag

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client"""
    return Mock()

@pytest.fixture
def mock_tool_manager():
    """Mock tool manager for testing"""
    tool_manager = Mock()
    tool_manager.execute_tool.return_value = "Mock tool execution result"
    return tool_manager

@pytest.fixture
def sample_query_request():
    """Sample query request data"""
    return {
        "query": "What is Python programming?",
        "session_id": "test_session_123"
    }

@pytest.fixture
def sample_query_response():
    """Sample query response data"""
    return {
        "answer": "Python is a programming language...",
        "sources": [
            {"title": "Python Basics Course", "url": "http://example.com/python"},
            {"title": "Advanced Python", "url": None}
        ],
        "session_id": "test_session_123"
    }

@pytest.fixture
def sample_course_stats():
    """Sample course statistics"""
    return {
        "total_courses": 3,
        "course_titles": ["Python Basics", "Advanced Python", "Data Science with Python"]
    }

@pytest.fixture
def temp_docs_directory():
    """Create temporary directory with sample course documents"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create sample course document
        course_content = """Course Title: Python Programming Basics
Course Link: https://example.com/python-course
Course Instructor: John Doe

Lesson 0: Introduction to Python
Lesson Link: https://example.com/lesson0
Python is a high-level, interpreted programming language known for its simplicity and readability.

Lesson 1: Variables and Data Types
Lesson Link: https://example.com/lesson1
In Python, variables are used to store data values. Python supports various data types including integers, floats, strings, and booleans.
"""
        course_file = os.path.join(temp_dir, "python_course.txt")
        with open(course_file, 'w') as f:
            f.write(course_content)
        
        yield temp_dir

@pytest.fixture
def test_app():
    """Create test FastAPI application"""
    # Import here to avoid circular import issues
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    # Create a minimal test app without static file mounting
    app = FastAPI(title="Test Course Materials RAG System")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app

@pytest.fixture
def client_with_mock_rag(test_app, mock_rag_system):
    """Create test client with mocked RAG system"""
    # Create API routes directly in test app to avoid import issues
    # This bypasses the problematic static file mounting in the main app
    from fastapi import HTTPException
    from pydantic import BaseModel
    from typing import List, Optional
    
    # Define models locally to avoid importing from app module
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class SourceInfo(BaseModel):
        title: str
        url: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceInfo]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]
    
    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            source_objects = []
            for source in sources:
                if isinstance(source, dict):
                    source_objects.append(SourceInfo(title=source['title'], url=source.get('url')))
                else:
                    source_objects.append(SourceInfo(title=str(source)))
            
            return QueryResponse(
                answer=answer,
                sources=source_objects,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        try:
            mock_rag_system.session_manager.clear_session(session_id)
            return {"success": True, "message": "Session cleared successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    with TestClient(test_app) as client:
        yield client

class MockResponse:
    """Mock Anthropic API response for testing"""
    
    def __init__(self, content: List[Dict], stop_reason: str = "end_turn"):
        self.content = [MockContentBlock(**block) for block in content]
        self.stop_reason = stop_reason

class MockContentBlock:
    """Mock content block for responses"""
    
    def __init__(self, type: str, text: str = None, name: str = None, 
                 input: Dict = None, id: str = None):
        self.type = type
        self.text = text
        self.name = name
        self.input = input or {}
        self.id = id or "test_id"

@pytest.fixture
def mock_anthropic_response():
    """Factory for creating mock Anthropic responses"""
    def _create_response(content_blocks: List[Dict], stop_reason: str = "end_turn"):
        return MockResponse(content_blocks, stop_reason)
    return _create_response

@pytest.fixture
def sample_tools():
    """Sample tools definition for testing"""
    return [{
        "name": "search_course_content",
        "description": "Search course content",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"]
        }
    }]