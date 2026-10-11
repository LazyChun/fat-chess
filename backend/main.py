"""
FatNotes 插件 fat-chess 后端入口。

职责：
- 注册 JSON-RPC handlers 供前端 sdk.backend.invoke 调用；
- 启动本地 HTTP 桥（127.0.0.1 随机端口），供宿主"下棋 MCP 工具"（requestUrl 类型）
  回调本进程，与 JSON-RPC 通道共享同一会话状态；
- 大模型走子：经 host_call("ai.chat") 调宿主 LLM，模型通过 MCP 工具落子。

RPC handlers（前端 sdk.backend.invoke("fatchess_rpc", {action, ...})）：
  new_game / get_state / legal_moves / make_move / undo / resign / ai_move
  list_games / delete_game / clear_games
  llm_move：fatchess_llm_move {gameId, modelId?}
  bridge_info：fatchess_bridge_info -> {port, baseUrl, ping}
"""

import sys

from engines.base import GameError
from engines.service import handle_rpc, handle_llm_move
from engines.bridge import get_bridge
from plugin_runtime import handler, run, host_get_plugin_config, host_set_plugin_config

_bridge_started = False


def _ensure_bridge() -> dict:
    global _bridge_started
    if not _bridge_started:
        get_bridge().start()
        _bridge_started = True
    b = get_bridge()
    return {"port": b.port, "baseUrl": b.base_url, "started": _bridge_started}


@handler("fatchess_bridge_info")
def fatchess_bridge_info(_params):
    return _ensure_bridge()


@handler("fatchess_rpc")
def fatchess_rpc(params):
    params = params or {}
    action = str(params.get("action") or "")
    if not action:
        raise GameError("缺少 action 参数")
    return handle_rpc(action, params)


@handler("fatchess_llm_move")
def fatchess_llm_move(params):
    return handle_llm_move(params or {})


@handler("fatchess_ping")
def fatchess_ping(_params):
    b = get_bridge()
    return {"pong": True, "bridge": b.port is not None, "port": b.port}


# 兼容示例 handler（保留骨架功能）
@handler("hello")
def hello(params):
    name = params.get("name", "World")
    return {"message": f"Hello from fat-chess backend, {name}!"}


@handler("getPluginConfig")
def get_plugin_config(_params):
    return host_get_plugin_config()


@handler("setPluginConfig")
def set_plugin_config(params):
    config_data = params.get("config", {}) if isinstance(params, dict) else {}
    merge = True
    if isinstance(params, dict):
        merge = bool(params.get("merge", True))
    return host_set_plugin_config(config_data, merge=merge)


if __name__ == "__main__":
    run()
