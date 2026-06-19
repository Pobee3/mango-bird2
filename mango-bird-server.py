#!/usr/bin/env python3
import json
import os
import stat
import urllib.error
import urllib.request
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = os.environ.get("MANGO_BIRD_HOST", "127.0.0.1")
PORT = int(os.environ.get("MANGO_BIRD_PORT", "8000"))
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = Path.home() / "Library" / "Application Support" / "Mango Bird"
MAX_BODY_BYTES = 64 * 1024
ALLOWED_MODES = {"fast", "thinking"}
PROVIDERS = {
    "deepseek": {
        "label": "DeepSeek",
        "api_url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-v4-flash",
    },
    "glm": {
        "label": "GLM",
        "api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model": "glm-4-flash",
    },
}


def configured_provider() -> str:
    provider = os.environ.get("MANGO_AI_PROVIDER", "deepseek").strip().lower()
    return provider if provider in PROVIDERS else "deepseek"


def configured_api_key() -> str:
    return os.environ.get("MANGO_AI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY", "")


def configured_api_url(provider: str) -> str:
    return (
        os.environ.get("MANGO_AI_API_URL")
        or os.environ.get("DEEPSEEK_API_URL")
        or PROVIDERS[provider]["api_url"]
    )


def configured_model(provider: str) -> str:
    return (
        os.environ.get("MANGO_AI_MODEL")
        or os.environ.get("DEEPSEEK_MODEL")
        or PROVIDERS[provider]["model"]
    )


def configured_mode() -> str:
    mode = os.environ.get("MANGO_AI_MODE") or os.environ.get("DEEPSEEK_MODE", "fast")
    return mode if mode in ALLOWED_MODES else "fast"
SYSTEM_PROMPT = (
    "你叫 Mango，是一只芒果青色小鸟，也是一个友好、可靠的中文知识助手。"
    "当需要自称时，只用 Mango，不要用小鸟、我这只小鸟等其他自称。"
    "优先直接回答用户的临时知识问题，内容准确、清楚、简洁。"
    "不知道或不确定时明确说明，不编造来源。"
    "默认使用中文，除非用户要求其他语言。"
    "保留一点温柔可爱的语气，但不要让语气妨碍信息表达。"
    "回答使用自然纯文本，不使用 Markdown 加粗、标题、表格或代码块，除非用户明确要求。"
    "尤其不要输出 ** 这类加粗标记。"
    "大多数普通回答不使用表情符号；只在鼓励、安慰、庆祝或轻松闲聊等确实合适的场景偶尔使用一个。"
    "不要每次固定使用表情，不要连续多轮重复相同表情，也不要堆叠多个表情。"
)


class MangoBirdHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_GET(self):
        if self.path == "/api/health":
            provider = configured_provider()
            self.send_json(
                200,
                {
                    "ok": True,
                    "configured": bool(configured_api_key()),
                    "provider": provider,
                    "providers": [
                        {"id": key, "label": item["label"]}
                        for key, item in PROVIDERS.items()
                    ],
                    "model": configured_model(provider),
                    "mode": configured_mode(),
                },
            )
            return
        super().do_GET()

    def do_POST(self):
        if self.path == "/api/config":
            self.handle_config_request()
            return

        if self.path != "/api/chat":
            self.send_json(404, {"error": "接口不存在。"})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            self.send_json(413, {"error": "消息内容过长。"})
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "请求格式不正确。"})
            return

        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            self.send_json(400, {"error": "没有可发送的消息。"})
            return

        cleaned = []
        for item in messages[-12:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role not in ("user", "assistant") or not isinstance(content, str):
                continue
            content = content.strip()
            if content:
                cleaned.append({"role": role, "content": content[:4000]})

        if not cleaned or cleaned[-1]["role"] != "user":
            self.send_json(400, {"error": "最后一条消息必须是用户问题。"})
            return

        provider = configured_provider()
        api_key = configured_api_key()
        if not api_key:
            self.send_json(
                503,
                {"error": "尚未设置 API Key，请设置后再聊天。"},
            )
            return

        requested_mode = payload.get("mode")
        model = configured_model(provider)
        default_mode = configured_mode()
        mode = requested_mode if requested_mode in ALLOWED_MODES else default_mode

        upstream_payload = {
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + cleaned,
            "stream": False,
            "temperature": 0.5,
            "max_tokens": 1200,
        }
        if provider == "deepseek" and mode == "thinking":
            upstream_payload["thinking"] = {"type": "enabled"}

        upstream_body = json.dumps(upstream_payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            configured_api_url(provider),
            data=upstream_body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.loads(response.read())
            if isinstance(result, dict) and result.get("error"):
                upstream_error = result["error"]
                if isinstance(upstream_error, dict):
                    upstream_error = upstream_error.get("message") or upstream_error.get("code")
                raise ValueError(f"upstream error: {upstream_error or 'unknown'}")
            message = result["choices"][0]["message"]
            answer = message.get("content") or message.get("reasoning_content") or ""
            answer = answer.strip()
            if not answer:
                raise ValueError("empty answer")
            answer = answer.replace("**", "")
            self.send_json(200, {"message": answer})
        except urllib.error.HTTPError as error:
            error_body = ""
            try:
                error_result = json.loads(error.read())
                upstream_error = error_result.get("error", {})
                error_body = upstream_error.get("message", "") if isinstance(
                    upstream_error, dict
                ) else str(upstream_error)
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                pass
            normalized_error = error_body.lower()
            detail = "模型服务请求失败，请稍后再试。"
            if error.code == 401:
                detail = "API Key 无效，请检查后重新保存。"
            elif error.code in (402, 403) or any(
                keyword in normalized_error
                for keyword in ("balance", "insufficient", "quota", "payment")
            ):
                detail = "账户余额不足，请充值后重试。"
            elif error.code == 429:
                detail = "请求过于频繁或额度不足，请稍后再试。"
            self.send_json(502, {"error": detail})
        except (urllib.error.URLError, TimeoutError):
            self.send_json(504, {"error": "连接模型服务超时，请检查网络。"})
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            self.send_json(502, {"error": "模型服务返回格式异常，请稍后再试。"})
        except ValueError as error:
            if "balance" in str(error).lower() or "insufficient" in str(error).lower():
                detail = "账户余额不足，请充值后重试。"
            elif "empty answer" in str(error):
                detail = "模型服务没有返回回答，请重新提问。"
            else:
                detail = "模型服务请求失败，请稍后再试。"
            self.send_json(502, {"error": detail})

    def handle_config_request(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > 4096:
            self.send_json(413, {"error": "API Key 内容过长。"})
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "请求格式不正确。"})
            return

        provider = payload.get("provider", "deepseek")
        if not isinstance(provider, str) or provider not in PROVIDERS:
            self.send_json(400, {"error": "请选择可用的模型服务。"})
            return

        api_key = payload.get("apiKey") or payload.get("deepseekApiKey")
        if not isinstance(api_key, str):
            self.send_json(400, {"error": "请输入 API Key。"})
            return

        api_key = api_key.strip()
        if "\n" in api_key or "\r" in api_key:
            self.send_json(400, {"error": "API Key 不能包含换行，请重新粘贴。"})
            return
        if len(api_key) < 12:
            self.send_json(400, {"error": "API Key 看起来太短，请检查后再保存。"})
            return

        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            env_file = CONFIG_DIR / ".env"
            env_file.write_text(
                "\n".join([
                    f"MANGO_AI_PROVIDER={provider}",
                    f"MANGO_AI_API_KEY={api_key}",
                    f"MANGO_AI_MODEL={PROVIDERS[provider]['model']}",
                    "",
                ]),
                encoding="utf-8",
            )
            env_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            self.send_json(500, {"error": "保存 API Key 失败，请检查本机权限。"})
            return

        os.environ["MANGO_AI_PROVIDER"] = provider
        os.environ["MANGO_AI_API_KEY"] = api_key
        os.environ["MANGO_AI_MODEL"] = PROVIDERS[provider]["model"]
        self.send_json(
            200,
            {
                "ok": True,
                "configured": True,
                "provider": provider,
                "model": PROVIDERS[provider]["model"],
            },
        )

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    handler = partial(MangoBirdHandler, directory=str(BASE_DIR))
    server = ThreadingHTTPServer((HOST, PORT), handler)
    actual_host, actual_port = server.server_address
    print(f"Mango Bird: http://{actual_host}:{actual_port}/mango-bird.html", flush=True)
    if not configured_api_key():
        print("提示：尚未设置 MANGO_AI_API_KEY，聊天功能暂不可用。", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMango Bird 已停止。")
    finally:
        server.server_close()
