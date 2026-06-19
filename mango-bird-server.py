#!/usr/bin/env python3
import json
import os
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


HOST = "127.0.0.1"
PORT = int(os.environ.get("MANGO_BIRD_PORT", "8000"))
MAX_BODY_BYTES = 64 * 1024
DEEPSEEK_URL = os.environ.get(
    "DEEPSEEK_API_URL",
    "https://api.deepseek.com/chat/completions",
)
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_MODE = os.environ.get("DEEPSEEK_MODE", "fast")
ALLOWED_MODELS = {"deepseek-v4-flash", "deepseek-v4-pro"}
ALLOWED_MODES = {"fast", "thinking"}
SYSTEM_PROMPT = (
    "你叫 Mango，是一只芒果黄色的小鸟，也是一个友好、可靠的中文知识助手。"
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
            self.send_json(
                200,
                {
                    "ok": True,
                    "configured": bool(os.environ.get("DEEPSEEK_API_KEY")),
                    "model": DEEPSEEK_MODEL,
                    "mode": DEEPSEEK_MODE if DEEPSEEK_MODE in ALLOWED_MODES else "fast",
                },
            )
            return
        super().do_GET()

    def do_POST(self):
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

        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            self.send_json(
                503,
                {"error": "尚未设置 DEEPSEEK_API_KEY，请设置后重新启动服务。"},
            )
            return

        requested_model = payload.get("model")
        model = requested_model if requested_model in ALLOWED_MODELS else DEEPSEEK_MODEL
        requested_mode = payload.get("mode")
        default_mode = DEEPSEEK_MODE if DEEPSEEK_MODE in ALLOWED_MODES else "fast"
        mode = requested_mode if requested_mode in ALLOWED_MODES else default_mode

        upstream_payload = {
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + cleaned,
            "stream": False,
            "temperature": 0.5,
            "max_tokens": 1200,
        }
        if mode == "thinking":
            upstream_payload["thinking"] = {"type": "enabled"}

        upstream_body = json.dumps(upstream_payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            DEEPSEEK_URL,
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
            detail = "DeepSeek 请求失败，请稍后再试。"
            if error.code == 401:
                detail = "DeepSeek API Key 无效，请检查环境变量。"
            elif error.code in (402, 403) or any(
                keyword in normalized_error
                for keyword in ("balance", "insufficient", "quota", "payment")
            ):
                detail = "DeepSeek 账户余额不足，请充值后重试。"
            elif error.code == 429:
                detail = "DeepSeek 请求过于频繁或额度不足，请稍后再试。"
            self.send_json(502, {"error": detail})
        except (urllib.error.URLError, TimeoutError):
            self.send_json(504, {"error": "连接 DeepSeek 超时，请检查网络。"})
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            self.send_json(502, {"error": "DeepSeek 返回格式异常，请稍后再试。"})
        except ValueError as error:
            if "balance" in str(error).lower() or "insufficient" in str(error).lower():
                detail = "DeepSeek 账户余额不足，请充值后重试。"
            elif "empty answer" in str(error):
                detail = "DeepSeek 没有返回回答，请重新提问。"
            else:
                detail = "DeepSeek 请求失败，请稍后再试。"
            self.send_json(502, {"error": detail})

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), MangoBirdHandler)
    print(f"Mango Bird: http://{HOST}:{PORT}/mango-bird.html")
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("提示：尚未设置 DEEPSEEK_API_KEY，聊天功能暂不可用。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMango Bird 已停止。")
    finally:
        server.server_close()
