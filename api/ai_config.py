# ai_config.py
import os
from typing import Optional


class AIConfig:
    """阿里云百炼大模型配置管理类（从示例项目移植）"""
    DEFAULT_REGION = "cn-beijing"

    def __init__(
        self,
        workspace_id: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        region: str = DEFAULT_REGION,
        api_base_path: str = "/compatible-mode/v1",
        timeout: float = 30.0,
        connect_timeout: float = 10.0,
        temperature: float = 0.7,
        max_retries: int = 1,
    ):
        if not workspace_id:
            raise ValueError("workspace_id 不能为空，请在控制台获取")
        self.workspace_id = workspace_id

        # API Key 优先从参数读取，否则从环境变量获取
        self.api_key = api_key or os.getenv("QWEN_TOKEN")
        self.model_name = model_name or "qwen-plus"
        self.region = region
        self.api_base_path = api_base_path
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.temperature = temperature
        self.max_retries = max_retries

    @property
    def base_url(self) -> str:
        """生成完整的 Base URL"""
        return f"https://{self.workspace_id}.{self.region}.maas.aliyuncs.com{self.api_base_path}"


config = AIConfig(
    workspace_id="ws-ak5rul7zg0gp9pp0",
    model_name="qwen3.7-flash-2026-07-15",
)
