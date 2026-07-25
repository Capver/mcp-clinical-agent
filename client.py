"""
Interactive Command-Line Interface for MCP Clinical Agent.

Orchestrates the MCP client connection, Ollama backend client initialization,
and the main REPL (Read-Eval-Print Loop). Supports multi-turn chat sessions, thread resets,
and tool execution diagnostics.
"""

import asyncio
import uuid
from pathlib import Path

from ollama import AsyncClient

from agent_graph import AgentState, build_agent_graph
from config import DEBUG_MODE, MODEL_NAME, SYSTEM_PROMPT
from mcp_client import MCPClient



async def main() -> None:
    """Run the multi-turn command-line client."""
    mcp_server_path = Path(__file__).with_name("mcp_server.py")

    async with MCPClient() as mcp_client:
        tool_names = await mcp_client.connect(mcp_server_path)

        if DEBUG_MODE:
            print("Connected to the MCP server.")
            print(f"Discovered tools: {tool_names}")


        ollama_client = AsyncClient()
        agent = build_agent_graph(
            mcp_client=mcp_client,
            ollama_client=ollama_client,
        )

        print(f"\nMCP Clinical Agent — {MODEL_NAME}")
        print("The current conversation remembers earlier messages.")
        print("Type '/reset' or '/new' to start a new conversation.")
        print("Type '/quit' or '/exit' to stop.")

        # Unique thread ID allows LangGraph's checkpointer to maintain session memory
        thread_id = str(uuid.uuid4())
        is_first_turn = True

        while True:
            question = input("\nQuestion: ").strip()

            if question.lower() in {"/quit", "/exit"}:
                break

            if question.lower() in {"/reset", "/new"}:
                thread_id = str(uuid.uuid4())
                is_first_turn = True
                print("Started a new conversation.")
                continue


            if not question:
                continue

            new_messages: list[dict[str, str]] = []

            # Prepend system prompt only on the first turn of a thread session
            if is_first_turn:
                new_messages.append(
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    }
                )

            new_messages.append(
                {
                    "role": "user",
                    "content": question,
                }
            )

            turn_input: AgentState = {
                "messages": new_messages,
                "tool_rounds": 0,
            }

            graph_config = {
                "configurable": {
                    "thread_id": thread_id,
                }
            }

            try:
                final_state = await agent.ainvoke(
                    turn_input,
                    config=graph_config,
                )

                is_first_turn = False

                final_message = final_state["messages"][-1]
                answer = final_message.get("content", "").strip()

                print(
                    "\nAnswer:\n"
                    f"{answer or 'The model returned no final answer.'}"
                )
                if DEBUG_MODE:
                    print(
                        f"\nTool rounds used this turn: "
                        f"{final_state['tool_rounds']}"
                    )


            except Exception as error:
                print(f"\nApplication error: {error}")


if __name__ == "__main__":
    asyncio.run(main())

