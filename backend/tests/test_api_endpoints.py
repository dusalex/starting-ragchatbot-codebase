import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
import sys
import os

# Add the backend directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.mark.api
class TestAPIEndpoints:
    """Test suite for FastAPI endpoints"""

    def test_query_endpoint_with_session_id(self, client_with_mock_rag, sample_query_request):
        """Test /api/query endpoint with provided session ID"""
        response = client_with_mock_rag.post("/api/query", json=sample_query_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == sample_query_request["session_id"]
        assert data["answer"] == "Test response"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["title"] == "Test Course"
        assert data["sources"][0]["url"] == "http://example.com"

    def test_query_endpoint_without_session_id(self, client_with_mock_rag):
        """Test /api/query endpoint without session ID (should create one)"""
        query_data = {"query": "What is Python?"}
        
        response = client_with_mock_rag.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert data["session_id"] == "test_session_123"  # From mock
        assert data["answer"] == "Test response"

    def test_query_endpoint_empty_query(self, client_with_mock_rag):
        """Test /api/query endpoint with empty query"""
        query_data = {"query": ""}
        
        response = client_with_mock_rag.post("/api/query", json=query_data)
        
        # Should still work - the RAG system handles empty queries
        assert response.status_code == 200

    def test_query_endpoint_missing_query_field(self, client_with_mock_rag):
        """Test /api/query endpoint with missing query field"""
        response = client_with_mock_rag.post("/api/query", json={})
        
        assert response.status_code == 422  # Validation error

    def test_query_endpoint_invalid_json(self, client_with_mock_rag):
        """Test /api/query endpoint with invalid JSON"""
        response = client_with_mock_rag.post(
            "/api/query", 
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_query_endpoint_rag_system_error(self, client_with_mock_rag, mock_rag_system):
        """Test /api/query endpoint when RAG system throws an error"""
        # Configure mock to raise an exception
        mock_rag_system.query.side_effect = Exception("RAG system error")
        
        query_data = {"query": "What is Python?"}
        response = client_with_mock_rag.post("/api/query", json=query_data)
        
        assert response.status_code == 500
        assert "RAG system error" in response.json()["detail"]

    def test_courses_endpoint_success(self, client_with_mock_rag):
        """Test /api/courses endpoint successful response"""
        response = client_with_mock_rag.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Test Course 1" in data["course_titles"]
        assert "Test Course 2" in data["course_titles"]

    def test_courses_endpoint_rag_system_error(self, client_with_mock_rag, mock_rag_system):
        """Test /api/courses endpoint when RAG system throws an error"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")
        
        response = client_with_mock_rag.get("/api/courses")
        
        assert response.status_code == 500
        assert "Analytics error" in response.json()["detail"]

    def test_clear_session_endpoint_success(self, client_with_mock_rag):
        """Test DELETE /api/session/{session_id} endpoint successful response"""
        session_id = "test_session_123"
        
        response = client_with_mock_rag.delete(f"/api/session/{session_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "Session cleared successfully" in data["message"]

    def test_clear_session_endpoint_empty_session_id(self, client_with_mock_rag):
        """Test DELETE /api/session/{session_id} with empty session ID"""
        response = client_with_mock_rag.delete("/api/session/")
        
        # Should return 404 for missing session_id path parameter
        assert response.status_code == 404

    def test_clear_session_endpoint_session_manager_error(self, client_with_mock_rag, mock_rag_system):
        """Test DELETE /api/session/{session_id} when session manager throws error"""
        mock_rag_system.session_manager.clear_session.side_effect = Exception("Session error")
        
        response = client_with_mock_rag.delete("/api/session/test_session")
        
        assert response.status_code == 500
        assert "Session error" in response.json()["detail"]

    def test_query_endpoint_backward_compatibility_string_sources(self, client_with_mock_rag, mock_rag_system):
        """Test /api/query endpoint handles backward compatible string sources"""
        # Configure mock to return old-style string sources
        mock_rag_system.query.return_value = ("Test response", ["Source 1", "Source 2"])
        
        query_data = {"query": "What is Python?"}
        response = client_with_mock_rag.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["sources"]) == 2
        assert data["sources"][0]["title"] == "Source 1"
        assert data["sources"][0]["url"] is None
        assert data["sources"][1]["title"] == "Source 2"
        assert data["sources"][1]["url"] is None

    def test_query_endpoint_mixed_source_formats(self, client_with_mock_rag, mock_rag_system):
        """Test /api/query endpoint handles mixed source formats"""
        mixed_sources = [
            {"title": "Course 1", "url": "http://example.com/1"},
            "String Source",
            {"title": "Course 2"}  # No URL
        ]
        mock_rag_system.query.return_value = ("Test response", mixed_sources)
        
        query_data = {"query": "What is Python?"}
        response = client_with_mock_rag.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["sources"]) == 3
        assert data["sources"][0]["title"] == "Course 1"
        assert data["sources"][0]["url"] == "http://example.com/1"
        assert data["sources"][1]["title"] == "String Source"
        assert data["sources"][1]["url"] is None
        assert data["sources"][2]["title"] == "Course 2"
        assert data["sources"][2]["url"] is None

    def test_cors_headers_present(self, client_with_mock_rag):
        """Test that CORS headers are properly set"""
        response = client_with_mock_rag.options("/api/query")
        
        # TestClient doesn't fully simulate CORS preflight, but we can test basic setup
        # The actual CORS middleware is configured in conftest.py
        assert response.status_code in [200, 405]  # OPTIONS might not be explicitly handled

    def test_content_type_headers(self, client_with_mock_rag, sample_query_request):
        """Test proper content-type handling"""
        response = client_with_mock_rag.post("/api/query", json=sample_query_request)
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_response_schema_validation(self, client_with_mock_rag, sample_query_request):
        """Test that response matches expected schema"""
        response = client_with_mock_rag.post("/api/query", json=sample_query_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate QueryResponse schema
        required_fields = ["answer", "sources", "session_id"]
        for field in required_fields:
            assert field in data
        
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)
        
        # Validate SourceInfo schema for each source
        for source in data["sources"]:
            assert "title" in source
            assert isinstance(source["title"], str)
            if "url" in source and source["url"] is not None:
                assert isinstance(source["url"], str)

    def test_courses_response_schema_validation(self, client_with_mock_rag):
        """Test that courses endpoint response matches expected schema"""
        response = client_with_mock_rag.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate CourseStats schema
        required_fields = ["total_courses", "course_titles"]
        for field in required_fields:
            assert field in data
        
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert data["total_courses"] >= 0
        
        # Validate all course titles are strings
        for title in data["course_titles"]:
            assert isinstance(title, str)

    def test_large_query_handling(self, client_with_mock_rag):
        """Test handling of large query strings"""
        large_query = "What is Python? " * 1000  # Create a large query
        query_data = {"query": large_query}
        
        response = client_with_mock_rag.post("/api/query", json=query_data)
        
        # Should handle large queries gracefully
        assert response.status_code == 200

    def test_unicode_query_handling(self, client_with_mock_rag):
        """Test handling of unicode characters in queries"""
        unicode_query = "What is Python? 你好 🐍 Ñiño"
        query_data = {"query": unicode_query}
        
        response = client_with_mock_rag.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        # Ensure the response is properly encoded
        data = response.json()
        assert isinstance(data["answer"], str)

@pytest.mark.integration
class TestEndToEndWorkflow:
    """Integration tests for complete workflows"""

    def test_session_workflow(self, client_with_mock_rag):
        """Test complete session workflow: create, query, clear"""
        # 1. Query without session (creates new session)
        query1_data = {"query": "What is Python?"}
        response1 = client_with_mock_rag.post("/api/query", json=query1_data)
        
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]
        
        # 2. Query with existing session
        query2_data = {"query": "Tell me more", "session_id": session_id}
        response2 = client_with_mock_rag.post("/api/query", json=query2_data)
        
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id
        
        # 3. Clear session
        response3 = client_with_mock_rag.delete(f"/api/session/{session_id}")
        
        assert response3.status_code == 200
        assert response3.json()["success"] is True

    def test_courses_and_query_workflow(self, client_with_mock_rag):
        """Test workflow of checking courses then querying"""
        # 1. Get course statistics
        courses_response = client_with_mock_rag.get("/api/courses")
        
        assert courses_response.status_code == 200
        courses_data = courses_response.json()
        assert courses_data["total_courses"] > 0
        
        # 2. Query based on available courses
        query_data = {"query": f"Tell me about {courses_data['course_titles'][0]}"}
        query_response = client_with_mock_rag.post("/api/query", json=query_data)
        
        assert query_response.status_code == 200
        query_data = query_response.json()
        assert len(query_data["sources"]) > 0