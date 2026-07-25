"""
LangGraph Agent Graph & State Management.

Coordinates LLM calls with Ollama, MCP tool invocations, turn-based tool limits, and
in-memory conversation checkpointing across user turns.
"""

from operator import add
from typing import Annotated, Any, Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from ollama import AsyncClient
from typing_extensions import TypedDict

from config import (
    DEBUG_MODE,
    MAX_TOOL_ROUNDS,
    MODEL_NAME,
    MODEL_THINKING,
    NUM_CTX,
    NUM_PREDICT,
    TEMPERATURE,
)
from mcp_client import MCPClient


class AgentState(TypedDict):
    """Information stored in one LangGraph conversation thread."""

    # Annotated with operator.add so returning new messages appends to history instead of overwriting
    messages: Annotated[list[dict[str, Any]], add]

    # Tracks tool execution turns within a single user request turn
    tool_rounds: int


def build_agent_graph(
    mcp_client: MCPClient,
    ollama_client: AsyncClient,
):
    """Construct and compile the LangGraph graph.

    Args:
        mcp_client: Connected MCP client providing tool definitions and execution handler.
        ollama_client: Asynchronous client for model generation.

    Returns:
        A compiled LangGraph executable with thread-based memory checkpointing.
    """

    async def call_model(state: AgentState) -> dict[str, Any]:
        """Invoke Ollama to reason on conversation history and generate text or tool requests."""
        model_messages = list(state["messages"])

        # Check if the agent has budget remaining for further tool calls
        tools_are_available = (
            state["tool_rounds"] < MAX_TOOL_ROUNDS
            and bool(mcp_client.ollama_tools)
        )

        # Force the model to synthesize a final answer when maximum tool rounds are reached
        if not tools_are_available:
            model_messages.append(
                {
                    "role": "system",
                    "content": (
                        "No more tool calls are available for this request. "
                        "Give the best final answer possible using the "
                        "information already returned by the tools."
                    ),
                }
            )

        chat_arguments: dict[str, Any] = {
            "model": MODEL_NAME,
            "messages": model_messages,
            "think": MODEL_THINKING,
            "stream": False,
            "options": {
                "num_ctx": NUM_CTX,
                "num_predict": NUM_PREDICT,
                "temperature": TEMPERATURE,
            },
        }

        if tools_are_available:
            chat_arguments["tools"] = mcp_client.ollama_tools

        response = await ollama_client.chat(**chat_arguments)

        # Preserve complete assistant message payload (including tool_calls and reasoning fields)
        assistant_message = response.message.model_dump(
            exclude_none=True
        )

        thinking = assistant_message.get("thinking") or getattr(
            response.message, "thinking", None
        )
        if thinking and DEBUG_MODE:
            print(f"\nModel Thinking:\n{thinking.strip()}\n")

        # Return new message to be appended by the state reducer
        return {
            "messages": [assistant_message],
        }

    async def execute_tools(state: AgentState) -> dict[str, Any]:
        """Execute every MCP tool requested in the last model message."""
        last_message = state["messages"][-1]
        tool_calls = last_message.get("tool_calls", [])
        tool_messages: list[dict[str, Any]] = []

        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            tool_name = function.get("name", "")
            arguments = function.get("arguments", {})

            if not tool_name:
                tool_result = "Tool call failed: no tool name was provided."
            elif not isinstance(arguments, dict):
                tool_result = (
                    "Tool call failed: the tool arguments were not an object."
                )
            else:
                if DEBUG_MODE:
                    print(
                        f"\nCalling MCP tool: {tool_name}"
                        f"\nArguments: {arguments}"
                    )

                tool_result = await mcp_client.call_tool(
                    tool_name,
                    arguments,
                )

                if DEBUG_MODE:
                    print(f"Tool result:\n{tool_result}")


            # Format tool response matching Ollama's expected schema (role='tool')
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": tool_result,
                }
            )

        return {
            "messages": tool_messages,
            "tool_rounds": state["tool_rounds"] + 1,
        }

    def choose_next_node(
        state: AgentState,
    ) -> Literal["execute_tools", "finish"]:
        """Conditional router deciding whether to loop to tool execution or terminate turn."""
        last_message = state["messages"][-1]

        if (
            last_message.get("tool_calls")
            and state["tool_rounds"] < MAX_TOOL_ROUNDS
        ):
            return "execute_tools"

        return "finish"

    # Assemble state graph workflow nodes and edges
    # pyrefly: ignore [bad-specialization]
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node(
        "call_model",
        call_model,
    )
    graph_builder.add_node(
        "execute_tools",
        execute_tools,
    )

    graph_builder.add_edge(
        START,
        "call_model",
    )

    graph_builder.add_conditional_edges(
        "call_model",
        choose_next_node,
        {
            "execute_tools": "execute_tools",
            "finish": END,
        },
    )

    graph_builder.add_edge(
        "execute_tools",
        "call_model",
    )

    # In-memory checkpointer maintains state across conversation turns indexed by thread_id
    checkpointer = InMemorySaver()

    return graph_builder.compile(
        checkpointer=checkpointer,
    )

