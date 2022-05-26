import sys
from typing import TYPE_CHECKING, Set

import pytest
from nonebug import App

if TYPE_CHECKING:
    from nonebot.plugin import Plugin


@pytest.mark.asyncio
async def test_load_plugin(app: App, load_plugin: Set["Plugin"]):
    import nonebot
    from nonebot.plugin import PluginManager

    loaded_plugins = {
        plugin for plugin in nonebot.get_loaded_plugins() if not plugin.parent_plugin
    }
    assert loaded_plugins == load_plugin

    # check simple plugin
    assert "plugins.export" in sys.modules

    # check sub plugin
    assert "plugins.nested.plugins.nested_subplugin" in sys.modules

    # check load again
    with pytest.raises(RuntimeError):
        PluginManager(plugins=["plugins.export"]).load_all_plugins()
    with pytest.raises(RuntimeError):
        PluginManager(search_path=["plugins"]).load_all_plugins()

    # check not found
    assert nonebot.load_plugin("some_plugin_not_exist") is None


@pytest.mark.asyncio
async def test_bad_plugin(app: App):
    import nonebot

    nonebot.load_plugins("bad_plugins")

    assert nonebot.get_plugin("bad_plugins") is None


@pytest.mark.asyncio
async def test_require_loaded(app: App, monkeypatch: pytest.MonkeyPatch):
    import nonebot

    def _patched_find(name: str):
        assert False

    monkeypatch.setattr("nonebot.plugin.load._find_manager_by_name", _patched_find)

    nonebot.load_plugin("plugins.export")

    nonebot.require("plugins.export")


@pytest.mark.asyncio
async def test_require_not_loaded(app: App, monkeypatch: pytest.MonkeyPatch):
    import nonebot
    from nonebot.plugin import PluginManager, _managers

    m = PluginManager(["plugins.export"])
    _managers.append(m)

    origin_load = PluginManager.load_plugin

    def _patched_load(self: PluginManager, name: str):
        assert self is m
        return origin_load(self, name)

    monkeypatch.setattr(PluginManager, "load_plugin", _patched_load)

    nonebot.require("plugins.export")

    assert len(_managers) == 1


@pytest.mark.asyncio
async def test_require_not_declared(app: App):
    import nonebot
    from nonebot.plugin import _managers

    nonebot.require("plugins.export")

    assert len(_managers) == 1
    assert _managers[-1].plugins == {"plugins.export"}


@pytest.mark.asyncio
async def test_require_not_found(app: App):
    import nonebot

    with pytest.raises(RuntimeError):
        nonebot.require("some_plugin_not_exist")
