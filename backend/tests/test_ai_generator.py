import os
import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the backend directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_generator import AIGenerator


class MockResponse:
    """Mock Anthropic API response for testing"""

    def __init__(self, content: List[Dict], stop_reason: str = "end_turn"):
        self.content = [MockContentBlock(**block) for block in content]
        self.stop_reason = stop_reason


class MockContentBlock:
    """Mock content block for responses"""

    def __init__(
        self,
        type: str,
        text: str = None,
        name: str = None,
        input: Dict = None,
        id: str = None,
    ):
        self.type = type
        self.text = text
        self.name = name
        self.input = input or {}
        self.id = id or "test_id"


class TestAIGenerator:
    """Test suite for AIGenerator sequential tool calling"""

    @pytest.fixture
    def ai_generator(self):
        """Create AIGenerator instance for testing"""
        return AIGenerator("test_api_key", "claude-3-sonnet-20241022")

    @pytest.fixture
    def mock_client(self):
        """Create mock Anthropic client"""
        return Mock()

    @pytest.fixture
    def mock_tool_manager(self):
        """Create mock tool manager"""
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "Mock tool result"
        return tool_manager

    @pytest.fixture
    def sample_tools(self):
        """Sample tools definition"""
        return [
            {
                "name": "search_course_content",
                "description": "Search course content",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            }
        ]

    def test_single_round_no_tools(self, ai_generator, mock_client):
        """Test single round response without tools"""
        # Mock response without tool use
        mock_response = MockResponse(
            [{"type": "text", "text": "Direct response without tools"}], "end_turn"
        )

        mock_client.messages.create.return_value = mock_response
        ai_generator.client = mock_client

        result = ai_generator.generate_response("What is Python?")

        assert result == "Direct response without tools"
        assert mock_client.messages.create.call_count == 1

        # Verify API call parameters
        call_args = mock_client.messages.create.call_args[1]
        assert len(call_args["messages"]) == 1
        assert call_args["messages"][0]["content"] == "What is Python?"
        assert "tools" not in call_args

    def test_single_round_with_tools_direct_response(
        self, ai_generator, mock_client, mock_tool_manager, sample_tools
    ):
        """Test single round where Claude gives direct response despite having tools"""
        # Mock response without tool use
        mock_response = MockResponse(
            [{"type": "text", "text": "I can answer this directly without searching"}],
            "end_turn",
        )

        mock_client.messages.create.return_value = mock_response
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            "What is Python?", tools=sample_tools, tool_manager=mock_tool_manager
        )

        assert result == "I can answer this directly without searching"
        assert mock_client.messages.create.call_count == 1

        # Verify tools were available in API call
        call_args = mock_client.messages.create.call_args[1]
        assert "tools" in call_args
        assert call_args["tools"] == sample_tools

    def test_two_round_sequential_tool_calling(
        self, ai_generator, mock_client, mock_tool_manager, sample_tools
    ):
        """Test two rounds of sequential tool calling"""
        # Round 1: Tool use response
        round1_response = MockResponse(
            [
                {
                    "type": "tool_use",
                    "name": "search_course_content",
                    "input": {"query": "Python basics"},
                    "id": "call_1",
                }
            ],
            "tool_use",
        )

        # Round 2: Another tool use response
        round2_response = MockResponse(
            [
                {
                    "type": "tool_use",
                    "name": "search_course_content",
                    "input": {"query": "advanced Python"},
                    "id": "call_2",
                }
            ],
            "tool_use",
        )

        # Final response after 2 rounds (max reached)
        final_response = MockResponse(
            [
                {
                    "type": "text",
                    "text": "Based on both searches, here's a comprehensive answer",
                }
            ],
            "end_turn",
        )

        mock_client.messages.create.side_effect = [
            round1_response,
            round2_response,
            final_response,
        ]
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            "Tell me about Python programming",
            tools=sample_tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,
        )

        assert result == "Based on both searches, here's a comprehensive answer"
        assert mock_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify tool calls
        tool_calls = mock_tool_manager.execute_tool.call_args_list
        assert tool_calls[0][0] == ("search_course_content",)
        assert tool_calls[0][1] == {"query": "Python basics"}
        assert tool_calls[1][0] == ("search_course_content",)
        assert tool_calls[1][1] == {"query": "advanced Python"}

    def test_mixed_content_terminates_early(
        self, ai_generator, mock_client, mock_tool_manager, sample_tools
    ):
        """Test that text + tool_use content terminates rounds early"""
        # Response with both text and tool call - should terminate
        mixed_response = MockResponse(
            [
                {"type": "text", "text": "Let me search for more info"},
                {
                    "type": "tool_use",
                    "name": "search_course_content",
                    "input": {"query": "Python"},
                    "id": "call_1",
                },
            ],
            "tool_use",
        )

        mock_client.messages.create.return_value = mixed_response
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            "What is Python?",
            tools=sample_tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,
        )

        assert result == "Let me search for more info"
        assert mock_client.messages.create.call_count == 1  # Only one round
        assert mock_tool_manager.execute_tool.call_count == 0  # No tools executed

    def test_tool_execution_error_handling(
        self, ai_generator, mock_client, mock_tool_manager, sample_tools
    ):
        """Test graceful handling of tool execution errors"""
        # Mock tool execution error
        mock_tool_manager.execute_tool.side_effect = Exception("Tool failed")

        # Round 1: Tool use
        round1_response = MockResponse(
            [
                {
                    "type": "tool_use",
                    "name": "search_course_content",
                    "input": {"query": "Python"},
                    "id": "call_1",
                }
            ],
            "tool_use",
        )

        # Round 2: Final response
        round2_response = MockResponse(
            [{"type": "text", "text": "I encountered an error but here's what I know"}],
            "end_turn",
        )

        mock_client.messages.create.side_effect = [round1_response, round2_response]
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            "What is Python?", tools=sample_tools, tool_manager=mock_tool_manager
        )

        assert result == "I encountered an error but here's what I know"
        assert mock_client.messages.create.call_count == 2

        # Verify error was passed to Claude
        second_call_args = mock_client.messages.create.call_args_list[1][1]
        messages = second_call_args["messages"]

        # Should have: user query, assistant tool call, user tool results
        assert len(messages) == 3
        assert messages[2]["role"] == "user"

        # Tool result should contain error message
        tool_results = messages[2]["content"]
        assert len(tool_results) == 1
        assert "Tool execution error: Tool failed" in tool_results[0]["content"]

    def test_max_rounds_termination(
        self, ai_generator, mock_client, mock_tool_manager, sample_tools
    ):
        """Test that max_rounds limit is enforced"""
        # Always return tool use responses (would cause infinite loop without limit)
        tool_response = MockResponse(
            [
                {
                    "type": "tool_use",
                    "name": "search_course_content",
                    "input": {"query": "test"},
                    "id": "call_1",
                }
            ],
            "tool_use",
        )

        mock_client.messages.create.return_value = tool_response
        ai_generator.client = mock_client

        # Set max_rounds to 1
        result = ai_generator.generate_response(
            "What is Python?",
            tools=sample_tools,
            tool_manager=mock_tool_manager,
            max_rounds=1,
        )

        # Should terminate after 1 round due to max_rounds limit
        assert mock_client.messages.create.call_count == 1
        assert mock_tool_manager.execute_tool.call_count == 0

    def test_conversation_history_integration(self, ai_generator, mock_client):
        """Test that conversation history is properly integrated"""
        mock_response = MockResponse(
            [{"type": "text", "text": "Response considering history"}], "end_turn"
        )

        mock_client.messages.create.return_value = mock_response
        ai_generator.client = mock_client

        result = ai_generator.generate_response(
            "Continue our discussion",
            conversation_history="Previous: Hello\nAssistant: Hi there!",
        )

        assert result == "Response considering history"

        # Verify conversation history in system prompt
        call_args = mock_client.messages.create.call_args[1]
        system_content = call_args["system"]
        assert "Previous conversation:" in system_content
        assert "Previous: Hello" in system_content

    def test_build_system_content_multi_round_instructions(self, ai_generator):
        """Test that system content includes multi-round instructions"""
        system_content = ai_generator._build_system_content(None, 2)

        assert "Tool Usage Protocol (Sequential):" in system_content
        assert (
            "You can make up to 2 tool calls across separate rounds" in system_content
        )
        assert "Multi-Round Strategy:" in system_content
        assert "Round 1: Use tools for initial information gathering" in system_content

    def test_should_continue_rounds_logic(self, ai_generator):
        """Test the round continuation logic"""

        # Test max rounds reached
        mock_response = MockResponse([{"type": "tool_use"}], "tool_use")
        assert not ai_generator._should_continue_rounds(mock_response, 2, 2)

        # Test no tool use
        mock_response = MockResponse([{"type": "text", "text": "Done"}], "end_turn")
        assert not ai_generator._should_continue_rounds(mock_response, 1, 2)

        # Test mixed content (text + tools)
        mock_response = MockResponse(
            [
                {"type": "text", "text": "Let me search"},
                {"type": "tool_use", "name": "search"},
            ],
            "tool_use",
        )
        assert not ai_generator._should_continue_rounds(mock_response, 1, 2)

        # Test should continue (tool use only, under limit)
        mock_response = MockResponse(
            [{"type": "tool_use", "name": "search"}], "tool_use"
        )
        assert ai_generator._should_continue_rounds(mock_response, 1, 2)

    def test_extract_final_response_fallback(self, ai_generator):
        """Test final response extraction with fallback"""

        # Test normal text extraction
        mock_response = MockResponse([{"type": "text", "text": "Normal response"}])
        result = ai_generator._extract_final_response(mock_response)
        assert result == "Normal response"

        # Test fallback when no text content
        mock_response = MockResponse([{"type": "tool_use", "name": "search"}])
        result = ai_generator._extract_final_response(mock_response)
        assert "unable to generate a complete response" in result

    def test_backward_compatibility_default_max_rounds(self, ai_generator, mock_client):
        """Test that default max_rounds maintains expected behavior"""
        mock_response = MockResponse([{"type": "text", "text": "Response"}], "end_turn")
        mock_client.messages.create.return_value = mock_response
        ai_generator.client = mock_client

        # Call without max_rounds parameter
        result = ai_generator.generate_response("Test query")

        assert result == "Response"
        # Should work with default max_rounds=2
        assert mock_client.messages.create.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
