#!/usr/bin/env python3
"""Lightweight proxy: translates Anthropic Messages API → OpenAI Chat Completions API.

Sits between Claude Code (which speaks /v1/messages) and apfel (which speaks
/v1/chat/completions). Forwards /v1/models as-is.
"""

import argparse
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError

upstream = "http://127.0.0.1:11434"
forward_tools = False


def anthropic_to_openai(body: dict) -> dict:
    """Convert Anthropic Messages request → OpenAI ChatCompletions request."""
    messages = []

    if body.get("system"):
        system = body["system"]
        if isinstance(system, list):
            system = " ".join(
                b["text"] for b in system if b.get("type") == "text"
            )
        messages.append({"role": "system", "content": system})

    for msg in body.get("messages", []):
        role = msg["role"]
        content = msg.get("content", "")

        if isinstance(content, str):
            messages.append({"role": role, "content": content})
        elif isinstance(content, list):
            # Flatten content blocks
            parts = []
            tool_calls = []
            tool_results = []
            for block in content:
                if block.get("type") == "text":
                    parts.append(block["text"])
                elif block.get("type") == "tool_use":
                    tool_calls.append({
                        "id": block["id"],
                        "type": "function",
                        "function": {
                            "name": block["name"],
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    })
                elif block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, list):
                        result_content = " ".join(
                            b.get("text", "") for b in result_content
                            if b.get("type") == "text"
                        )
                    tool_results.append({
                        "tool_call_id": block["tool_use_id"],
                        "role": "tool",
                        "content": str(result_content),
                    })

            if tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": " ".join(parts) if parts else None,
                    "tool_calls": tool_calls,
                })
            elif parts:
                messages.append({"role": role, "content": " ".join(parts)})

            for tr in tool_results:
                messages.append(tr)

    # Always use apple-foundationmodel — Claude Code may send other model names
    # (e.g. claude-haiku for internal tasks) that apfel would reject.
    req = {
        "model": "apple-foundationmodel",
        "messages": messages,
        "stream": body.get("stream", False),
    }

    if "max_tokens" in body:
        req["max_tokens"] = body["max_tokens"]
    if "temperature" in body:
        req["temperature"] = body["temperature"]

    # Apple Intelligence has a 4096-token context window.
    # Tool schemas are huge and would blow through the limit,
    # so we only forward tools if explicitly enabled.
    if body.get("tools") and forward_tools:
        req["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            }
            for t in body["tools"]
        ]

    return req


def openai_to_anthropic(oai: dict, model: str) -> dict:
    """Convert OpenAI ChatCompletions response → Anthropic Messages response."""
    choice = oai.get("choices", [{}])[0]
    message = choice.get("message", {})

    content = []
    if message.get("content"):
        content.append({"type": "text", "text": message["content"]})

    for tc in message.get("tool_calls", []):
        fn = tc.get("function", {})
        try:
            args = json.loads(fn.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}
        content.append({
            "type": "tool_use",
            "id": tc["id"],
            "name": fn["name"],
            "input": args,
        })

    stop_reason = "end_turn"
    finish = choice.get("finish_reason", "")
    if finish == "tool_calls":
        stop_reason = "tool_use"
    elif finish == "length":
        stop_reason = "max_tokens"

    usage = oai.get("usage", {})
    return {
        "id": oai.get("id", "msg_proxy"),
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content if content else [{"type": "text", "text": ""}],
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


def openai_stream_to_anthropic_stream(oai_lines, model: str):
    """Yield Anthropic SSE events from OpenAI SSE stream."""
    yield event_line("message_start", {
        "type": "message_start",
        "message": {
            "id": "msg_proxy",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [],
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        },
    })

    block_idx = 0
    started_text = False
    current_tool_id = None

    for raw_line in oai_lines:
        line = raw_line.decode("utf-8", errors="replace").strip()
        if not line.startswith("data: "):
            continue
        data = line[6:]
        if data == "[DONE]":
            break

        try:
            chunk = json.loads(data)
        except json.JSONDecodeError:
            continue

        delta = chunk.get("choices", [{}])[0].get("delta", {})

        # Text content
        if delta.get("content"):
            if not started_text:
                yield event_line("content_block_start", {
                    "type": "content_block_start",
                    "index": block_idx,
                    "content_block": {"type": "text", "text": ""},
                })
                started_text = True
            yield event_line("content_block_delta", {
                "type": "content_block_delta",
                "index": block_idx,
                "delta": {"type": "text_delta", "text": delta["content"]},
            })

        # Tool calls
        if delta.get("tool_calls"):
            for tc in delta["tool_calls"]:
                tc_id = tc.get("id")
                fn = tc.get("function", {})
                if tc_id and tc_id != current_tool_id:
                    if started_text:
                        yield event_line("content_block_stop", {
                            "type": "content_block_stop",
                            "index": block_idx,
                        })
                        block_idx += 1
                        started_text = False
                    current_tool_id = tc_id
                    yield event_line("content_block_start", {
                        "type": "content_block_start",
                        "index": block_idx,
                        "content_block": {
                            "type": "tool_use",
                            "id": tc_id,
                            "name": fn.get("name", ""),
                            "input": {},
                        },
                    })
                if fn.get("arguments"):
                    yield event_line("content_block_delta", {
                        "type": "content_block_delta",
                        "index": block_idx,
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": fn["arguments"],
                        },
                    })

        finish = chunk.get("choices", [{}])[0].get("finish_reason")
        if finish:
            yield event_line("content_block_stop", {
                "type": "content_block_stop",
                "index": block_idx,
            })
            stop_reason = "end_turn"
            if finish == "tool_calls":
                stop_reason = "tool_use"
            elif finish == "length":
                stop_reason = "max_tokens"
            yield event_line("message_delta", {
                "type": "message_delta",
                "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                "usage": {"output_tokens": 0},
            })

    yield event_line("message_stop", {"type": "message_stop"})


def event_line(event_type: str, data: dict) -> bytes:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n".encode()


class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[proxy] {args[0]}", file=sys.stderr)

    def _path_without_query(self):
        return self.path.split("?")[0]

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        path = self._path_without_query()
        if path in ("/v1/models", "/health"):
            self._forward_get()
        else:
            self.send_error(404)

    def do_POST(self):
        path = self._path_without_query()
        if path == "/v1/messages":
            self._handle_messages()
        elif path == "/v1/messages/count_tokens":
            self._handle_count_tokens()
        else:
            self.send_error(404)

    def _forward_get(self):
        try:
            req = Request(f"{upstream}{self.path}")
            with urlopen(req, timeout=10) as resp:
                body = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
        except HTTPError as e:
            self.send_error(e.code)

    def _handle_count_tokens(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"input_tokens": 100}).encode())

    def _handle_messages(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        body = json.loads(raw)

        model = body.get("model", "apple-foundationmodel")
        oai_body = anthropic_to_openai(body)
        stream = body.get("stream", False)


        try:
            oai_req = Request(
                f"{upstream}/v1/chat/completions",
                data=json.dumps(oai_body).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            if stream:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()

                with urlopen(oai_req, timeout=120) as resp:
                    for event_bytes in openai_stream_to_anthropic_stream(
                        resp, model
                    ):
                        self.wfile.write(event_bytes)
                        self.wfile.flush()
            else:
                with urlopen(oai_req, timeout=120) as resp:
                    oai_resp = json.loads(resp.read())

                anthropic_resp = openai_to_anthropic(oai_resp, model)
                result = json.dumps(anthropic_resp).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(result)

        except HTTPError as e:
            body = e.read().decode()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body.encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": {"type": "proxy_error", "message": str(e)}
            }).encode())


def main():
    global upstream
    parser = argparse.ArgumentParser(description="Anthropic→OpenAI proxy for apfel")
    parser.add_argument("--port", type=int, default=11435)
    parser.add_argument("--upstream", default="http://127.0.0.1:11434")
    parser.add_argument("--forward-tools", action="store_true",
                        help="Forward tool schemas to upstream (disabled by default to save context)")
    args = parser.parse_args()
    upstream = args.upstream
    forward_tools = args.forward_tools

    server = HTTPServer(("127.0.0.1", args.port), ProxyHandler)
    print(f"Proxy listening on http://127.0.0.1:{args.port} → {upstream}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()
