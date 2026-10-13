"""JSON-RPC message framing for LSP stdio transport."""
import json

# ── Hard limits — DoS protection ─────────────────────────────────────────
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB per message body
MAX_HEADER_SIZE = 8192                  # 8 KB per header block
MAX_BUFFER_SIZE = 20 * 1024 * 1024      # 20 MB max pending buffer


class FramingError(Exception):
    pass


def encode_message(msg: dict) -> bytes:
    body = json.dumps(msg, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\ncharset=utf-8\r\n".encode("ascii")
    return header + b"\r\n" + body


def decode_messages(data: bytes) -> tuple[list[dict], bytes]:
    messages = []
    remainder = data
    while True:
        header_end = remainder.find(b"\r\n\r\n")
        if header_end == -1:
            # No complete header — check buffer isn't growing unboundedly
            if len(remainder) > MAX_HEADER_SIZE:
                raise FramingError(f"Header block exceeds {MAX_HEADER_SIZE} bytes")
            break
        if header_end > MAX_HEADER_SIZE:
            raise FramingError(f"Header block exceeds {MAX_HEADER_SIZE} bytes")
        header_block = remainder[:header_end].decode("ascii")
        content_length = None
        for line in header_block.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    raise FramingError(f"Invalid Content-Length header: {line}")
                break
        if content_length is None:
            raise FramingError("Missing Content-Length header")
        if content_length > MAX_CONTENT_LENGTH:
            raise FramingError(f"Content-Length {content_length} exceeds max {MAX_CONTENT_LENGTH}")
        if content_length < 0:
            raise FramingError(f"Negative Content-Length: {content_length}")
        body_start = header_end + 4
        body_end = body_start + content_length
        if len(remainder) < body_end:
            # Incomplete body — ensure the pending buffer can't grow forever
            if len(remainder) > MAX_BUFFER_SIZE:
                raise FramingError(f"Pending buffer exceeds {MAX_BUFFER_SIZE} bytes")
            break
        body = remainder[body_start:body_end]
        try:
            msg = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise FramingError(f"Invalid JSON body: {e}")
        messages.append(msg)
        remainder = remainder[body_end:]
    return messages, remainder
