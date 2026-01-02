import random

from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.components import At, Plain, Reply
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

from .utils import get_ats, get_reply_id


class MultimsgPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    async def send(
        self, event: AiocqhttpMessageEvent, payload: dict, forward: bool = False
    ):
        """发送消息"""
        if event.is_private_chat():
            payload["user_id"] = int(event.get_sender_id())
            action = "send_private_forward_msg" if forward else "send_private_msg"
        else:
            payload["group_id"] = int(event.get_group_id())
            action = "send_group_forward_msg" if forward else "send_group_msg"

        try:
            result = await event.bot.api.call_action(action, **payload)
            event.stop_event()
            return result
        except Exception as e:
            logger.error(f"[MultimsgPlugin] 调用 {action} 出错: {e}")
            return None

    @filter.command("text")
    async def send_text(self, event: AiocqhttpMessageEvent):
        """text <文本>"""
        text = event.message_str.removeprefix("text").strip()
        payload = {"message": [{"type": "text", "data": {"text": text}}]}
        await self.send(event, payload)

    @filter.command("face")
    async def send_face(
        self,
        event: AiocqhttpMessageEvent,
        face_id: int | str | None = None,
        count: int = 1,
    ):
        """face <ID> <数量>"""

        def _face(fid: int) -> dict:
            return {"type": "face", "data": {"id": fid}}

        if isinstance(face_id, str) and "~" in face_id:
            start, end = map(int, face_id.split("~"))
            message = [_face(i) for i in range(start, end + 1) for _ in range(count)]
        else:
            fid = face_id if isinstance(face_id, int) else random.randint(1, 500)
            message = [_face(int(fid)) for _ in range(count)]

        await self.send(event, {"message": message})

    @filter.command("dice", alias={"骰子"})
    async def send_dice(self, event: AiocqhttpMessageEvent):
        payload = {"message": [{"type": "dice"}]}
        await self.send(event, payload)

    @filter.command("rps", alias={"猜拳", "石头", "剪刀", "布"})
    async def send_rps(self, event: AiocqhttpMessageEvent):
        """猜拳|石头|剪刀|布"""
        payload = {"message": [{"type": "rps"}]}
        await self.send(event, payload)

    @filter.command("at", alias={"@"})
    async def send_at(
        self,
        event: AiocqhttpMessageEvent,
        qq: str | int | None = None,
        text: str | None = None,
    ):
        """at QQ|@某人|all"""

        def at_msg(user_id: str | int):
            return {"type": "at", "data": {"qq": str(user_id)}}

        group_id = int(event.get_group_id())
        self_id = int(event.get_self_id())
        user_ids = get_ats(event)
        message: list[dict] = []

        match qq:
            case "all" | "全员" | "全体成员":
                if not event.is_admin():
                    return
                role = (
                    await event.bot.get_group_member_info(
                        group_id=group_id, user_id=self_id, no_cache=True
                    )
                ).get("role")

                if role in {"owner", "admin"}:
                    # 有权限 → 直接全体
                    message.append(at_msg("all"))
                else:
                    # 没权限 → 一个个 @
                    members = await event.bot.get_group_member_list(group_id=group_id)
                    message.extend(
                        at_msg(m["user_id"]) for m in members if m.get("user_id")
                    )

            case s if s and str(s).isdigit():
                message.append(at_msg(s))

            case _ if user_ids:
                message.extend(at_msg(uid) for uid in user_ids)

            case _:
                result: dict = await event.bot.get_group_msg_history(group_id=group_id)
                target_ids = [
                    msg["sender"]["user_id"] for msg in result.get("messages", [])
                ]
                message.extend(at_msg(uid) for uid in set(target_ids))
        if text:
            message.append({"type": "text", "data": {"text": " " + text}})
        await self.send(event, {"message": message})

    @filter.command("contact", alias={"推荐"})
    async def contact(self, event: AiocqhttpMessageEvent):
        """推荐 群号/@群友/@qq"""
        args = event.message_str.removeprefix("推荐").strip().split()
        gids, uids = [], []
        for arg in args:
            if arg.isdigit():
                gids.append(arg)
            elif arg.startswith("@") and arg[1:].isdigit():
                uids.append(arg[1:])

        uids.extend(get_ats(event))

        if not uids and not gids:
            if random.random() < 0.5:
                friend_list = await event.bot.get_friend_list()
                uids.append(random.choice(friend_list)["user_id"])
            else:
                group_list = await event.bot.get_group_list()
                gids.append(random.choice(group_list)["group_id"])

        if uids:
            for uid in uids:
                payload = {
                    "message": [
                        {"type": "contact", "data": {"type": "qq", "id": int(uid)}}
                    ],
                }
                await self.send(event, payload)
            return

        if not gids:
            group_list = await event.bot.get_group_list()
            gids.append(random.choice(group_list)["group_id"])
        for gid in gids:
            payload = {
                "message": [
                    {"type": "contact", "data": {"type": "group", "id": int(gid)}}
                ],
            }
            await self.send(event, payload)

    @filter.command("music")
    async def send_music(
        self,
        event: AiocqhttpMessageEvent,
        music_type: str | int | None = "163",
        music_id: int | None = 1495009565,
    ):
        """music <平台> <ID>"""
        payload = {
            "message": [
                {
                    "type": "music",
                    "data": {
                        "type": str(music_type),
                        "id": str(music_id),
                    },
                }
            ],
        }
        await self.send(event, payload)

    @filter.command("markdown", alias={"md"})
    async def send_md(self, event: AiocqhttpMessageEvent, content: str = ""):
        """发送markdown消息"""
        sender_id = int(event.get_self_id())
        sender_name = event.get_sender_name()
        content = content.partition(" ")[2] or self.config["default_md"]
        payload = {
            "message": [
                {
                    "type": "node",
                    "data": {
                        "user_id": sender_id,
                        "nickname": sender_name,
                        "content": [
                            {
                                "type": "node",
                                "data": {
                                    "user_id": sender_id,
                                    "nickname": sender_name,
                                    "content": [
                                        {
                                            "type": "markdown",
                                            "data": {"content": content},
                                        },
                                    ],
                                },
                            },
                        ],
                    },
                },
            ],
            "prompt": "[Markdown消息]",
            "summary": "[Markdown消息]",
            "source": "Markdown消息",
            "news": [{"text": "新版QQ需转发一次才可见"}],
        }
        await self.send(event, payload, forward=True)

    @filter.command("node")
    async def send_node(self, event: AiocqhttpMessageEvent):
        """(引用消息)node 标题 内容"""
        print(event.message_obj.message)
        source = news = prompt = summary = None
        user_id = nickname = reply_id = None

        for seg in event.get_messages():
            match seg:
                case Plain(text=text):
                    _, source, news_text, prompt, summary, *_ = (
                        text.split() + [None] * 5
                    )

                    source = source or "合并转发"
                    if not news_text:
                        news = None
                    elif news_text == "0":
                        news = [{"text": ""}]
                    else:
                        news = [{"text": news_text}]

                case At(qq=qq, name=name):
                    user_id, nickname = int(qq), name

                case Reply(id=id_):
                    reply_id = int(id_)

        if not reply_id:
            return

        payload = {
            "message": [
                {
                    "type": "node",
                    "data": {
                        "user_id": user_id,
                        "nickname": nickname,
                        "id": reply_id,
                    },
                }
            ],
            "prompt": prompt,
            "summary": summary,
            "source": source,
            "news": news,
        }
        await self.send(event, payload, forward=True)

    @filter.command("forward", alias={"转发"})
    async def send_forward(
        self, event: AiocqhttpMessageEvent, tid: str | int | None = None
    ):
        """转发引用的消息"""
        message_id = get_reply_id(event)
        if not message_id:
            return

        user_ids = (
            [tid]
            if tid and str(tid).startswith("@") and str(tid)[1:].isdigit()
            else get_ats(event)
        )
        if user_ids:
            for uid in user_ids:
                try:
                    await event.bot.forward_friend_single_msg(
                        user_id=int(uid), message_id=message_id
                    )
                except Exception as e:
                    logger.error(f"[MultimsgPlugin] 转发到好友 {uid} 出错: {e}")
            return
        else:
            group_id = tid if tid and str(tid).isdigit() else event.get_group_id()
            try:
                await event.bot.forward_group_single_msg(
                    group_id=int(group_id), message_id=message_id
                )
            except Exception as e:
                logger.error(f"[MultimsgPlugin] 转发到群 {group_id} 出错: {e}")
        event.stop_event()
        return
