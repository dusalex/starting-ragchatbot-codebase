from typing import Any, Dict, List, Optional, Tuple

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Tool Usage Guidelines:
- **Content Search Tool**: Use `search_course_content` for questions about specific course content, lessons, or detailed educational materials
- **Course Outline Tool**: Use `get_course_outline` for questions about course structure, lesson lists, course overview, or complete course outlines
- **Sequential Tool Calling**: You can make up to 2 tool calls across separate rounds to gather comprehensive information
- After each tool call, you'll see the results and can decide if additional searches are needed
- Use multiple rounds for complex queries requiring information from different courses or lessons
- Synthesize tool results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course content questions**: Use content search tool first, then answer
- **Course outline/structure questions**: Use outline tool first, then answer - include course title, course link, and complete lesson list with numbers and titles
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
        max_rounds: int = 2,
    ) -> str:
        """
        Generate AI response with sequential tool calling support.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool calling rounds (default 2)

        Returns:
            Generated response as string
        """

        # Build system content with multi-round context
        system_content = self._build_system_content(conversation_history, max_rounds)

        # Initialize conversation state
        messages = [{"role": "user", "content": query}]
        current_round = 0

        while current_round < max_rounds:
            current_round += 1

            # Execute conversation round
            response, tool_used = self._execute_conversation_round(
                messages, system_content, tools, tool_manager
            )

            # Add assistant response to conversation
            messages.append({"role": "assistant", "content": response.content})

            # Check termination conditions
            if not self._should_continue_rounds(response, current_round, max_rounds):
                break

            # If tools were used, add results and continue
            if tool_used and tool_manager:
                tool_results = self._execute_tools(response, tool_manager)
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})

        # Extract final text response
        return self._extract_final_response(response)

    def _execute_conversation_round(
        self,
        messages: List[Dict],
        system_content: str,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> Tuple[Any, bool]:
        """
        Execute a single round of conversation.

        Args:
            messages: Current conversation messages
            system_content: System prompt content
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Tuple of (response, tool_used_flag)
        """
        # Prepare API parameters for this round
        api_params = {
            **self.base_params,
            "messages": messages.copy(),
            "system": system_content,
        }

        # Add tools if available
        tools_available = tools is not None
        if tools_available:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Make API call
        response = self.client.messages.create(**api_params)

        # Determine if tools were used
        tool_used = response.stop_reason == "tool_use"

        return response, tool_used

    def _should_continue_rounds(
        self, response, current_round: int, max_rounds: int
    ) -> bool:
        """
        Determine whether to continue with another round.

        Termination conditions:
        1. Reached max rounds
        2. No tool use in current response
        3. Response contains text content (Claude provided final answer)

        Args:
            response: API response from current round
            current_round: Current round number (1-indexed)
            max_rounds: Maximum allowed rounds

        Returns:
            True if should continue to next round, False to terminate
        """

        # Hard limit reached
        if current_round >= max_rounds:
            return False

        # No tool use means Claude chose to give direct answer
        if response.stop_reason != "tool_use":
            return False

        # If response has both tool calls AND text, Claude is providing final answer
        has_text = any(
            block.type == "text" and block.text.strip() for block in response.content
        )
        has_tools = any(block.type == "tool_use" for block in response.content)

        if has_text and has_tools:
            return False  # Claude provided reasoning + tool call = final answer

        return has_tools  # Continue only if there are tool calls to process

    def _build_system_content(
        self, conversation_history: Optional[str], max_rounds: int
    ) -> str:
        """Build system prompt with multi-round context"""

        multi_round_instructions = f"""
Tool Usage Protocol (Sequential):
- You can make up to {max_rounds} tool calls across separate rounds
- After each tool call, you'll see the results and can decide next actions
- Use additional tool calls to gather more specific information if needed
- Provide your final response when you have sufficient information
- Include reasoning about why additional searches might be helpful

Multi-Round Strategy:
- Round 1: Use tools for initial information gathering
- Round 2: Use tools for follow-up questions or specific details if needed
- Always synthesize information from all rounds in your final response
"""

        base_prompt = self.SYSTEM_PROMPT.replace(
            "- **Sequential Tool Calling**: You can make up to 2 tool calls across separate rounds to gather comprehensive information",
            multi_round_instructions,
        )

        if conversation_history:
            return f"{base_prompt}\n\nPrevious conversation:\n{conversation_history}"

        return base_prompt

    def _execute_tools(self, response, tool_manager) -> Optional[List[Dict]]:
        """Execute tools and return results for next round"""

        tool_results = []

        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    # Execute tool
                    result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": result,
                        }
                    )

                except Exception as e:
                    # Handle tool execution errors gracefully
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Tool execution error: {str(e)}",
                        }
                    )

        return tool_results if tool_results else None

    def _extract_final_response(self, response) -> str:
        """Extract final text response from the last API response"""

        # Look for text content in the response
        for block in response.content:
            if block.type == "text" and block.text.strip():
                return block.text

        # Fallback: if no text found, return a generic message
        return "I apologize, but I was unable to generate a complete response. Please try rephrasing your question."
