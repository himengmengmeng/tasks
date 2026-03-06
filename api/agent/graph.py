"""
LangGraph Agent using the ReAct pattern.
The agent uses OpenAI GPT with tools bound for CRUD operations.
"""
import os
import logging
from typing import AsyncGenerator
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

from .prompts import SYSTEM_PROMPT, CONVERSATION_NAMING_PROMPT
from .tools import get_all_tools

load_dotenv()
logger = logging.getLogger(__name__)

# LLM instances
_chat_llm = None
_naming_llm = None


def get_chat_llm():
    """Get or create the chat LLM instance (DeepSeek)."""
    global _chat_llm
    if _chat_llm is None:
        _chat_llm = ChatOpenAI(
            model="deepseek-chat",
            temperature=0.7,
            streaming=True,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
    return _chat_llm


def get_naming_llm():
    """Get or create the naming LLM instance (DeepSeek, non-streaming, low temp)."""
    global _naming_llm
    if _naming_llm is None:
        _naming_llm = ChatOpenAI(
            model="deepseek-chat",
            temperature=0,
            streaming=False,
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
    return _naming_llm


def create_agent_graph(user_id: int):
    """
    Create a LangGraph agent graph with tools bound for a specific user.
    The user_id is injected into the system prompt so the LLM knows to pass it.
    """
    tools = get_all_tools()
    llm = get_chat_llm()
    llm_with_tools = llm.bind_tools(tools)

    system_message = SystemMessage(content=SYSTEM_PROMPT + f"\n\nCurrent user_id: {user_id}. You MUST pass user_id={user_id} in every tool call.")

    async def agent_node(state: MessagesState):
        """The agent node that calls the LLM."""
        messages = [system_message] + state["messages"]
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    def should_continue(state: MessagesState):
        """Decide whether to continue to tools or end."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    tool_node = ToolNode(tools)

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


async def stream_agent_response(
    user_id: int,
    user_message: str,
    history: list[dict],
) -> AsyncGenerator[dict, None]:
    """
    Stream the agent response for a user message.
    
    Yields dicts with event types:
    - {"type": "token", "content": "partial text"}
    - {"type": "tool_call", "name": "tool_name", "args": {...}}
    - {"type": "tool_result", "name": "tool_name", "result": "..."}
    - {"type": "done", "full_content": "complete response", "tool_calls_data": [...]}
    - {"type": "error", "detail": "error message"}
    """
    try:
        graph = create_agent_graph(user_id)

        messages = []
        for msg in history:
            if msg["role"] == "human":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "ai":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))

        full_content = ""
        tool_calls_data = []

        async for event in graph.astream_events(
            {"messages": messages},
            version="v2",
        ):
            kind = event.get("event")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    full_content += chunk.content
                    yield {"type": "token", "content": chunk.content}

                if chunk and hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                    pass  # Tool call chunks are partial, we handle full calls below

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = event.get("data", {}).get("input", {})
                tool_calls_data.append({
                    "name": tool_name,
                    "args": tool_input,
                    "result": None
                })
                yield {"type": "tool_call", "name": tool_name, "args": tool_input}

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                tool_output = event.get("data", {}).get("output", "")
                if isinstance(tool_output, ToolMessage):
                    tool_output = tool_output.content
                for tc in tool_calls_data:
                    if tc["name"] == tool_name and tc["result"] is None:
                        tc["result"] = str(tool_output)[:500]
                        break
                yield {"type": "tool_result", "name": tool_name, "result": str(tool_output)[:500]}

        yield {
            "type": "done",
            "full_content": full_content,
            "tool_calls_data": tool_calls_data if tool_calls_data else None,
        }

    except Exception as e:
        logger.error(f"Agent streaming error: {str(e)}", exc_info=True)
        yield {"type": "error", "detail": str(e)}


async def generate_conversation_name(messages: list[dict]) -> str:
    """Generate a concise conversation name from message history."""
    try:
        conversation_text = ""
        for msg in messages[:6]:
            role = "User" if msg["role"] == "human" else "AI"
            content = msg["content"][:200]
            conversation_text += f"{role}: {content}\n"

        llm = get_naming_llm()
        prompt = CONVERSATION_NAMING_PROMPT.format(conversation=conversation_text)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        name = response.content.strip().strip('"').strip("'")
        return name[:100]
    except Exception as e:
        logger.error(f"Error generating conversation name: {str(e)}")
        return "New Conversation"
