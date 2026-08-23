from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from .ai_config import config
from .system_prompt import SYSTEM_PROMPT


async def load_agent(user_info: dict = None):
    if not config.api_key:
        raise RuntimeError("未设置 QWEN_TOKEN 环境变量，无法调用 AI")
    llm = ChatOpenAI(
        model=config.model_name,
        api_key=config.api_key,
        base_url=config.base_url,
    )

    system_message = SYSTEM_PROMPT
    if user_info:
        system_message += (
            f"\n# 当前用户\n"
            f"你的对话者是 **{user_info.get('name', '未知')}**（学号：{user_info.get('student_id', '未知')}）。\n"
        )

    # ponytail: 参考项目通过 MCP 挂载工具 + MemorySaver 记忆（依赖独立 MCP 进程）；
    # 这里去掉 MCP 工具，对话记忆改由数据库会话历史提供（见 ChatStreamView）。
    agent_executor = create_agent(
        model=llm,
        system_prompt=system_message,
    )
    return agent_executor


async def run_agent_stream(messages: list[dict], user_info: dict = None):
    """messages: 完整对话历史（含最新用户消息），以 SSE token 流式返回"""
    inputs = {"messages": messages}
    agent = await load_agent(user_info)

    async for event in agent.astream_events(inputs, {}, version="v2"):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if chunk.content:
                yield chunk.content
