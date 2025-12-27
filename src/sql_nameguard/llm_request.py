from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence, Union

Role = Literal["system", "user", "assistant", "tool"]

@dataclass(frozen=True)
class ImagePart:
    """
    Provider-agnostic image payload.

    Store images as base64 strings (no data: prefix).
    Keep mime_type explicit so each provider adapter can map correctly.
    """
    b64: str
    mime_type: str = "image/png"

@dataclass(frozen=True)
class TextPart:
    text: str

ContentPart = Union[TextPart, ImagePart]

@dataclass(frozen=True)
class Message:
    role: Role
    parts: List[ContentPart]

    @staticmethod
    def text(role: Role, text: str) -> "Message":
        return Message(role=role, parts=[TextPart(text=text)])

    @staticmethod
    def text_and_images(role: Role, text: str, images: Sequence[ImagePart]) -> "Message":
        parts: List[ContentPart] = [TextPart(text=text)]
        parts.extend(list(images))
        return Message(role=role, parts=parts)

@dataclass
class LLMRequest:
    """
    Canonical request object for calling LLM providers with requests.post().

    - Keep provider differences OUT of this class.
    - Put all normalization here; each provider adapter serializes it.
    """
    provider: Literal["openai", "anthropic", "google"]
    model: str

    messages: List[Message] = field(default_factory=list)

    max_tokens: int = 1000
    temperature: float = 0.3

    # Optional knobs you may want later
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    seed: Optional[int] = None

    # Optional: metadata for logging / tracing in your pipeline
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not self.model or not isinstance(self.model, str):
            raise ValueError("LLMRequest.model must be a non-empty string.")

        if self.provider not in ("openai", "anthropic", "google"):
            raise ValueError(f"Unsupported provider: {self.provider}")

        if not isinstance(self.messages, list) or len(self.messages) == 0:
            raise ValueError("LLMRequest.messages must be a non-empty list.")

        if not isinstance(self.max_tokens, int) or self.max_tokens <= 0:
            raise ValueError("LLMRequest.max_tokens must be a positive int.")

        if not isinstance(self.temperature, (int, float)) or not (0.0 <= float(self.temperature) <= 2.0):
            raise ValueError("LLMRequest.temperature must be between 0.0 and 2.0.")

        # Validate message structure
        for i, m in enumerate(self.messages):
            if m.role not in ("system", "user", "assistant", "tool"):
                raise ValueError(f"messages[{i}].role is invalid: {m.role}")

            if not isinstance(m.parts, list) or len(m.parts) == 0:
                raise ValueError(f"messages[{i}].parts must be a non-empty list.")

            for j, p in enumerate(m.parts):
                if isinstance(p, TextPart):
                    if not isinstance(p.text, str):
                        raise ValueError(f"messages[{i}].parts[{j}].text must be a string.")
                elif isinstance(p, ImagePart):
                    if not isinstance(p.b64, str) or not p.b64.strip():
                        raise ValueError(f"messages[{i}].parts[{j}].b64 must be a non-empty base64 string.")
                    if not isinstance(p.mime_type, str) or "/" not in p.mime_type:
                        raise ValueError(f"messages[{i}].parts[{j}].mime_type must look like 'image/png'.")
                else:
                    raise ValueError(f"messages[{i}].parts[{j}] is not a supported ContentPart type.")

    # Convenience helpers
    def add_text(self, role: Role, text: str) -> None:
        self.messages.append(Message.text(role=role, text=text))
        self._validate()

    def add_text_and_images(self, role: Role, text: str, images: Sequence[ImagePart]) -> None:
        self.messages.append(Message.text_and_images(role=role, text=text, images=images))
        self._validate()

    def system_text(self) -> Optional[str]:
        """
        Returns the concatenated system text (if any) as a convenience for adapters.
        """
        sys_parts: List[str] = []
        for m in self.messages:
            if m.role == "system":
                for p in m.parts:
                    if isinstance(p, TextPart):
                        sys_parts.append(p.text)
        if not sys_parts:
            return None
        return "\n".join(sys_parts)

    def without_system_messages(self) -> List[Message]:
        """
        Convenience for providers that want `system` separated (Anthropic).
        """
        return [m for m in self.messages if m.role != "system"]
    
    def messages_as_json(self) -> str:
        """
        Serialize messages into a JSON-serializable list of dicts suitable for requests.post(json=...).

        Each message becomes: {"role": "<role>", "content": [ ... ] }
        - Text parts: {"type": "text", "text": "<text>"}
        - Image parts: {"type": "image", "b64": "<base64>", "mime_type": "<mime/type>"}
        """
        json_msgs = []
        for m in self.messages:
            part_list: List[Dict[str, Any]] = []
            for p in m.parts:
                if isinstance(p, TextPart):
                    part_list.append({"type": "text", "text": p.text})
                elif isinstance(p, ImagePart):
                    part_list.append({"type": "image_url", "image_url": { "url": f"data:image/png;base64,{p.b64}" }})
                else:
                    # Shouldn't happen due to validation, but skip unknown types defensively.
                    continue
            json_msgs.append({"role": m.role, "content": part_list})
        return json_msgs
