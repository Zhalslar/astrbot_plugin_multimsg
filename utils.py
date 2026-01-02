from astrbot.core.message.components import At, Reply
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)


def get_ats(event: AiocqhttpMessageEvent) -> list[int]:
    """获取被at者们的id列表"""
    return [
        int(seg.qq)
        for seg in event.get_messages()
        if (isinstance(seg, At) and str(seg.qq) != event.get_self_id())
    ]

def get_reply_id(event: AiocqhttpMessageEvent) -> int | None:
    """获取被引用消息的id"""
    for seg in event.get_messages():
        if isinstance(seg, Reply):
            return int(seg.id)


