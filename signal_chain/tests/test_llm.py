"""模型调用组装。不访问 DeepSeek，也不启动 Claude Agent SDK。"""

import pytest

from signal_chain.agents.llm import MODEL, AgentFailed, assemble_call


def test_call_uses_deepseek_flash_and_hides_the_key():
    spec = assemble_call("只根据材料评级", model=MODEL, api_key="sk-test-secret")
    assert spec["model"] == "deepseek-flash"
    assert spec["tools"] == []
    assert spec["allowed_tools"] == []
    assert spec["env"]["ANTHROPIC_BASE_URL"] == "https://api.deepseek.com/anthropic"
    assert spec["env"]["ANTHROPIC_API_KEY"] == "sk-test-secret"
    assert "sk-test-secret" not in spec["prompt"]


def test_key_in_prompt_is_rejected():
    with pytest.raises(AgentFailed):
        assemble_call("密钥 sk-test-secret 不要出现", model=MODEL, api_key="sk-test-secret")
