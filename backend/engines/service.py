"""
fat-chess 服务层：RPC 动作分发（JSON-RPC 与 HTTP 桥共用同一实现），
以及"大模型走子"编排（经 host_call 调宿主 ai.chat，让模型调用下棋 MCP 工具）。
"""

from __future__ import annotations

import json
import threading
from typing import Any, Dict, List, Optional

# 导入各棋种模块以触发注册（register_game 装饰器）
from . import go as _go  # noqa: F401
from . import gomoku as _gomoku  # noqa: F401
from . import xiangqi as _xiangqi  # noqa: F401
from . import chess as _chess  # noqa: F401
from . import jungle as _jungle  # noqa: F401
from . import junqi as _junqi  # noqa: F401
from .base import GameError, SessionStore

# 串行化所有棋局操作（JSON-RPC 线程池 + HTTP 线程可能并发访问同一对局）
_rpc_lock = threading.RLock()
_store = SessionStore()

GAMES = ["go", "gomoku", "xiangqi", "chess", "jungle", "junqi"]

# 每个棋种注册到宿主的 MCP 工具名（前端据此注册/更新）
TOOL_PREFIX = "fatchess"


def tool_ids_for(game: str) -> List[str]:
    return [f"{TOOL_PREFIX}_{game}_new_game", f"{TOOL_PREFIX}_{game}_get_state",
            f"{TOOL_PREFIX}_{game}_legal_moves", f"{TOOL_PREFIX}_{game}_make_move",
            f"{TOOL_PREFIX}_{game}_undo"]


def _game_not_found(game_id: str) -> GameError:
    return GameError(f"对局不存在: {game_id}")


def handle_rpc(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    with _rpc_lock:
        fn = _ACTIONS.get(action)
        if fn is None:
            raise GameError(f"未知操作: {action}")
        return fn(params or {})


# ---------------------------------------------------------------------------
# 动作实现
# ---------------------------------------------------------------------------

def _new_game(p: Dict[str, Any]) -> Dict[str, Any]:
    game_kind = str(p.get("game") or "")
    if game_kind not in GAMES:
        raise GameError(f"未知棋种: {game_kind!r}")
    settings = p.get("settings")
    settings = settings if isinstance(settings, dict) else {}
    sess = _store.create(
        p.get("gameId") or None,
        game_kind,
        mode=str(p.get("mode") or "ai"),
        settings=settings,
        model_id=p.get("modelId") or None,
        ai_side=int(p.get("aiSide") or 1),
        ai_level=int(p.get("aiLevel") or 1),
    )
    return {
        "gameId": sess.id,
        "game": game_kind,
        "mode": sess.mode,
        "state": sess.game.get_state(),
        "aiSide": sess.ai_side,
        "aiLevel": sess.ai_level,
        "modelId": sess.model_id,
    }


def _get_state(p: Dict[str, Any]) -> Dict[str, Any]:
    sess = _store.get(str(p.get("gameId") or ""))
    return {"gameId": sess.id, "game": sess.game.GAME_ID, "state": sess.game.get_state()}


def _legal_moves(p: Dict[str, Any]) -> Dict[str, Any]:
    sess = _store.get(str(p.get("gameId") or ""))
    side = _side_arg(p, sess)
    return {"gameId": sess.id, "moves": sess.game.legal_moves(side),
            "turn": sess.game.turn, "winner": sess.game.winner}


def _make_move(p: Dict[str, Any]) -> Dict[str, Any]:
    sess = _store.get(str(p.get("gameId") or ""))
    move = str(p.get("move") or "")
    if not move:
        raise GameError("缺少走法参数 move")
    side = _side_arg(p, sess)
    st = sess.game.make_move(move, side)
    return {"gameId": sess.id, "state": st, "move": move}


def _undo(p: Dict[str, Any]) -> Dict[str, Any]:
    sess = _store.get(str(p.get("gameId") or ""))
    return {"gameId": sess.id, "state": sess.game.undo()}


def _resign(p: Dict[str, Any]) -> Dict[str, Any]:
    sess = _store.get(str(p.get("gameId") or ""))
    side = _side_arg(p, sess)
    return {"gameId": sess.id, "state": sess.game.resign(side)}


def _ai_move(p: Dict[str, Any]) -> Dict[str, Any]:
    sess = _store.get(str(p.get("gameId") or ""))
    side = _side_arg(p, sess)
    level = int(p.get("level") or sess.ai_level or 1)
    sess.ai_level = level
    move = sess.game.ai_move(side, level)
    st = sess.game.make_move(move, side)
    return {"gameId": sess.id, "state": st, "move": move}


def _list_games(_p: Dict[str, Any]) -> Dict[str, Any]:
    return {"games": _store.list()}


def _delete_game(p: Dict[str, Any]) -> Dict[str, Any]:
    _store.delete(str(p.get("gameId") or ""))
    return {"ok": True}


def _clear_games(_p: Dict[str, Any]) -> Dict[str, Any]:
    _store.clear()
    return {"ok": True}


def _side_arg(p: Dict[str, Any], sess) -> int:
    side = p.get("side")
    if side is None:
        return sess.game.turn
    return int(side)


_ACTIONS = {
    "new_game": _new_game,
    "get_state": _get_state,
    "legal_moves": _legal_moves,
    "make_move": _make_move,
    "undo": _undo,
    "resign": _resign,
    "ai_move": _ai_move,
    "list_games": _list_games,
    "delete_game": _delete_game,
    "clear_games": _clear_games,
}


# ---------------------------------------------------------------------------
# 大模型走子编排
# ---------------------------------------------------------------------------

_GAME_RULES: Dict[str, str] = {
    "go": "围棋：坐标 a0.. 起，pass 表示虚着。X=黑方先手，O=白方。连续两次虚着终局按数空判定胜负。",
    "gomoku": "五子棋：15x15，坐标 a0..o14，直接落子坐标即可（如 j7）。先连成五子者胜。X=黑方先手，O=白方。",
    "xiangqi": "中国象棋：坐标 a0..i9，走法为 fromto（如 b0c2，红马跳）。大写红方先手，小写黑方。将死或困毙判负。",
    "chess": "国际象棋：坐标 a0..h7（0 行=第 8 横线），走法 UCI（如 e2e4、e7e8q 升变）。白方先手。",
    "jungle": "斗兽棋：7x9，坐标 a0..i6，走法 fromto。象>狮>虎>豹>狼>狗>猫>鼠，鼠吃象；进对方兽穴胜。大写蓝方先手。",
    "junqi": "军棋（明盘）：9x10，坐标 a0..i9，走法 fromto。司令>军长>...>工兵，工兵挖雷，炸弹同归于尽；军旗被吃即负。大写黑方先手。",
}

_SYSTEM_TMPL = (
    "你正在与用户进行{name}对弈（{game}）。\n"
    "{rules}\n\n"
    "对局已由系统创建，你无需新建对局。请按以下步骤行动：\n"
    "1) 需要时先用 get_state / legal_moves 工具查看局面与合法走法；\n"
    "2) 用 make_move 工具落子（参数 gameId 与 move，move 必须来自 legal_moves 的合法走法）；\n"
    "3) 落子成功后用一句简短中文说明你的着法。\n"
    "绝对不要替用户落子，也不要直接输出走法而不调用工具；每回合只走一步。\n"
    "当前局面如下：\n"
    "```\n"
    "{board}\n"
    "```\n"
)


def llm_move(game_id: str, model_id: Optional[str], extra_prompt: Optional[str] = None) -> Dict[str, Any]:
    """让宿主大模型走一步棋。返回 {state, content, moved}。"""
    from .base import GAME_FACTORY
    from plugin_runtime import host_call

    sess = _store.get(game_id)
    game = sess.game
    if game.winner is not None:
        raise GameError("对局已结束")
    if not model_id:
        model_id = sess.model_id
    if not model_id:
        raise GameError("未选择大模型，请先在设置中选择模型")

    name = GAME_FACTORY[game.GAME_ID].NAME
    system = _SYSTEM_TMPL.format(
        name=name, game=game.GAME_ID,
        rules=_GAME_RULES.get(game.GAME_ID, ""),
        board=game.to_text(),
    )
    user = "现在轮到你走棋。请查看局面并落子。"
    if extra_prompt:
        user += " 额外要求：" + extra_prompt
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    tool_ids = tool_ids_for(game.GAME_ID)

    before = len(game.history)
    result = host_call("ai.chat", {
        "modelId": model_id,
        "messages": messages,
        "toolIds": tool_ids,
        "maxIterations": 12,
    }, timeout=300)

    content = str(result.get("content") or "")
    tool_steps = result.get("toolSteps") or []
    moved = len(game.history) > before
    return {
        "state": game.get_state(),
        "content": content,
        "moved": moved,
        "toolSteps": tool_steps,
        "model": result.get("model", ""),
    }


# ---------------------------------------------------------------------------
# 大模型走子入口（不占用 RPC 全局锁，避免与工具回调死锁）
# ---------------------------------------------------------------------------

_thinking: set = set()


def _mark_thinking(game_id: str, on: bool) -> None:
    with _rpc_lock:
        if on:
            _thinking.add(game_id)
        else:
            _thinking.discard(game_id)


def handle_llm_move(params: Dict[str, Any]) -> Dict[str, Any]:
    game_id = str(params.get("gameId") or "")
    sess = _store.get(game_id)
    with _rpc_lock:
        if game_id in _thinking:
            raise GameError("对方正在思考中，请稍候")
        _thinking.add(game_id)
    try:
        return llm_move(game_id, params.get("modelId"), params.get("extraPrompt"))
    finally:
        _mark_thinking(game_id, False)
