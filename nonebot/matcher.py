#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import typing
from functools import wraps
from datetime import datetime
from collections import defaultdict

from nonebot.rule import Rule
from nonebot.permission import Permission, EVERYBODY, USER
from nonebot.typing import Bot, Event, Handler
from nonebot.typing import Type, List, Dict, Optional, NoReturn
from nonebot.exception import PausedException, RejectedException, FinishedException

matchers: Dict[int, List[Type["Matcher"]]] = defaultdict(list)


class Matcher:
    """`Matcher`类
    """

    rule: Rule = Rule()
    permission: Permission = Permission()
    handlers: List[Handler] = []
    temp: bool = False
    expire_time: Optional[datetime] = None
    priority: int = 1

    _default_state: dict = {}

    # _default_parser: Optional[Callable[[Event, dict], None]] = None
    # _args_parser: Optional[Callable[[Event, dict], None]] = None

    def __init__(self):
        """实例化 Matcher 以便运行
        """
        self.handlers = self.handlers.copy()
        self.state = self._default_state.copy()
        # self.parser = self._args_parser or self._default_parser

    @classmethod
    def new(cls,
            rule: Rule = Rule(),
            permission: Permission = Permission(),
            handlers: list = [],
            temp: bool = False,
            priority: int = 1,
            *,
            default_state: dict = {},
            expire_time: Optional[datetime] = None) -> Type["Matcher"]:
        """创建新的 Matcher

        Returns:
            Type["Matcher"]: 新的 Matcher 类
        """

        NewMatcher = type(
            "Matcher", (Matcher,), {
                "rule": rule,
                "permission": permission,
                "handlers": handlers,
                "temp": temp,
                "expire_time": expire_time,
                "priority": priority,
                "_default_state": default_state
            })

        matchers[priority].append(NewMatcher)

        return NewMatcher

    @classmethod
    async def check_perm(cls, bot: Bot, event: Event) -> bool:
        return await cls.permission(bot, event)

    @classmethod
    async def check_rule(cls, bot: Bot, event: Event, state: dict) -> bool:
        """检查 Matcher 的 Rule 是否成立

        Args:
            event (Event): 消息事件

        Returns:
            bool: 条件成立与否
        """
        return await cls.rule(bot, event, state)

    # @classmethod
    # def args_parser(cls, func: Callable[[Event, dict], None]):
    #     cls._default_parser = func
    #     return func

    @classmethod
    def handle(cls):
        """直接处理消息事件"""

        def _decorator(func: Handler) -> Handler:
            cls.handlers.append(func)
            return func

        return _decorator

    @classmethod
    def receive(cls):
        """接收一条新消息并处理"""

        def _decorator(func: Handler) -> Handler:

            async def _handler(bot: Bot, event: Event, state: dict) -> NoReturn:
                raise PausedException

            cls.handlers.append(_handler)
            cls.handlers.append(func)

            return func

        return _decorator

    # @classmethod
    # def got(cls,
    #         key: str,
    #         prompt: Optional[str] = None,
    #         args_parser: Optional[Callable[[Event, dict], None]] = None):

    #     def _decorator(func: Handler) -> Handler:

    #         @wraps(func)
    #         def _handler(event: Event, state: dict):
    #             if key not in state:
    #                 if state.get("__current_arg__", None) == key:
    #                     state[key] = event.message
    #                     del state["__current_arg__"]
    #                     return func(event, state)
    #                 state["__current_arg__"] = key
    #                 cls._args_parser = args_parser
    #                 raise RejectedException

    #             return func(event, state)

    #         cls.handlers.append(_handler)

    #         return func

    #     return _decorator

    # @classmethod
    # def finish(cls, prompt: Optional[str] = None):
    #     raise FinishedException

    # @classmethod
    # def reject(cls, prompt: Optional[str] = None):
    #     raise RejectedException

    # 运行handlers
    async def run(self, bot: Bot, event: Event, state):
        try:
            # if self.parser:
            #     await self.parser(event, state)  # type: ignore

            # Refresh preprocess state
            self.state.update(state)

            for _ in range(len(self.handlers)):
                handler = self.handlers.pop(0)
                annotation = typing.get_type_hints(handler)
                BotType = annotation.get("bot")
                if BotType and not isinstance(bot, BotType):
                    continue
                await handler(bot, event, self.state)
        except RejectedException:
            self.handlers.insert(0, handler)  # type: ignore
            matcher = Matcher.new(
                self.rule,
                USER(event.user_id, perm=self.permission),  # type:ignore
                self.handlers,
                temp=True,
                priority=0,
                default_state=self.state,
                expire_time=datetime.now() + bot.config.session_expire_timeout)
            matchers[0].append(matcher)
            return
        except PausedException:
            matcher = Matcher.new(
                self.rule,
                USER(event.user_id, perm=self.permission),  # type:ignore
                self.handlers,
                temp=True,
                priority=0,
                default_state=self.state,
                expire_time=datetime.now() + bot.config.session_expire_timeout)
            matchers[0].append(matcher)
            return
        except FinishedException:
            return
