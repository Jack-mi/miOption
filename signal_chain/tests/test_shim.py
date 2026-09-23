"""8799 翻译 shim 的格式转换单测（不依赖真实路由）。"""

from signal_chain.router_shim import chat_to_responses, responses_to_chat


def test_chat_to_responses_roles():
    req = chat_to_responses({
        "model": "glm-5.3",
        "messages": [
            {"role": "system", "content": "你是助手"},
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！"},
            {"role": "user", "content": "再问"},
        ],
        "max_tokens": 100,
    })
    assert req["model"] == "glm-5.3"
    assert req["instructions"] == "你是助手"
    assert req["max_output_tokens"] == 100
    roles = [i["role"] for i in req["input"]]
    assert roles == ["user", "assistant", "user"]
    assert req["input"][1]["content"][0]["type"] == "output_text"


def test_responses_to_chat_extracts_text():
    resp = {
        "id": "resp_1",
        "object": "response",
        "output": [
            {"type": "reasoning", "content": [{"type": "reasoning_text", "text": "思考"}]},
            {"type": "message", "content": [{"type": "output_text", "text": "正常"}]},
        ],
        "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
    }
    chat = responses_to_chat(resp, "kimi-k3")
    assert chat["object"] == "chat.completion"
    assert chat["choices"][0]["message"]["content"] == "正常"  # 不含 reasoning
    assert chat["usage"]["total_tokens"] == 12
