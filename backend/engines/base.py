"""
fat-chess 引擎公共基类与坐标工具。

统一约定（供 UI 与大模型使用，全插件一致）：

- 文本坐标：棋盘左上角为原点，列用字母 a..（左→右），行用数字 0..（上→下）。
  例如围棋 19 路 (0,0) -> "a0"，五子棋 (14,14) -> "o14"，
  国际象棋标准 a8 在本系统为 "a0"（黑方视角朝上即与标准棋盘一致）。
- 走法字符串：静态棋类为 "fromto"（如国际象棋 "e2e4"、"e7e8q"；
  中国象棋 "b0c2"）；落子类（围棋/五子棋）为单个坐标 "j9"。
- 颜色：0 = 先手（黑/红），1 = 后手（白/黑/蓝）。

每个具体游戏实现 GameBase 并注册到 GAME_FACTORY。
"""

from __future__ import annotations

import time
import threading
from typing import Any, Callable, Dict, List, Optional


class GameError(ValueError):
    """棋局非法操作（非法走法/未轮到/对局已结束等）。"""


# ---------------------------------------------------------------------------
# 坐标工具
# ---------------------------------------------------------------------------

def col_letter(col: int) -> str:
    return chr(ord("a") + col)


def parse_square(sq: str) -> tuple:
    """'a0' -> (0,0)。非法输入抛 GameError。"""
    if not isinstance(sq, str) or len(sq) < 2:
        raise GameError(f"非法坐标: {sq!r}")
    col = ord(sq[0].lower()) - ord("a")
    try:
        row = int(sq[1:])
    except ValueError:
        raise GameError(f"非法坐标: {sq!r}") from None
    return row, col


def sq_text(row: int, col: int) -> str:
    return f"{col_letter(col)}{row}"


def move_text(a: tuple, b: tuple, promo: str = "") -> str:
    return sq_text(*a) + sq_text(*b) + promo


# ---------------------------------------------------------------------------
# 游戏基类
# ---------------------------------------------------------------------------

class GameBase:
    GAME_ID: str = "base"
    NAME: str = "base"
    # 允许的额外设置字段（new_game settings 里可传入）
    SETTINGS: tuple = ()

    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []  # 每步: {move, side, captured, ...}
        self.turn: int = 0
        self.winner: Optional[int] = None  # None 进行中, 0/1 胜负, -1 和棋
        self.ended_reason: str = ""
        self.created_at: float = time.time()
        self.settings: Dict[str, Any] = {}

    # ---- 子类必须实现 ----
    def reset(self, settings: Optional[Dict[str, Any]] = None) -> None:
        raise NotImplementedError

    def legal_moves(self, side: int) -> List[str]:
        raise NotImplementedError

    def apply_move(self, move: str, side: int) -> None:
        """校验并落子；非法抛 GameError。落子后更新 turn/winner。"""
        raise NotImplementedError

    def state(self) -> Dict[str, Any]:
        """返回 UI 渲染用的完整状态（必须 JSON 可序列化）。"""
        raise NotImplementedError

    # ---- 公共能力 ----
    def make_move(self, move: str, side: Optional[int] = None) -> Dict[str, Any]:
        if self.winner is not None:
            raise GameError("对局已结束")
        side = self.turn if side is None else side
        if side != self.turn:
            raise GameError("未轮到该方走子")
        self.apply_move(move, side)
        return self.get_state()

    def undo(self) -> Dict[str, Any]:
        if not self.history:
            raise GameError("没有可悔的棋")
        self.history.pop()
        self._replay()
        return self.get_state()

    def _replay(self) -> None:
        """从空盘重放历史（悔棋后恢复状态）。各引擎 apply_move 自行写入 history。"""
        saved = [h["move"] for h in self.history]
        self.reset(self.settings)
        self.history = []
        for m in saved:
            self.apply_move(m, self.turn)

    def resign(self, side: int) -> Dict[str, Any]:
        if self.winner is not None:
            raise GameError("对局已结束")
        self.winner = 1 - side
        self.ended_reason = "resign"
        return self.get_state()

    def to_text(self) -> str:
        """面向大模型的纯文本局面描述（子类覆盖）。"""
        return ""

    def ai_move(self, side: int, level: int = 1) -> str:
        """本地引擎走子，返回走法；无棋可走抛 GameError。"""
        from .ai import pick_move
        moves = self.legal_moves(side)
        if not moves:
            raise GameError("无棋可走")
        return pick_move(self, moves, side, level)

    def get_state(self) -> Dict[str, Any]:
        st = self.state()
        st.setdefault("game", self.GAME_ID)
        st.setdefault("text", self.to_text())
        return st


# ---------------------------------------------------------------------------
# 会话管理
# ---------------------------------------------------------------------------

class GameSession:
    def __init__(self, game_id: str, game: GameBase, mode: str = "ai",
                 settings: Optional[Dict[str, Any]] = None) -> None:
        self.id = game_id
        self.game = game
        self.mode = mode  # "ai" | "llm" | "pvp"
        self.model_id: Optional[str] = None
        self.ai_side: int = 1
        self.ai_level: int = 1
        self.created_at = time.time()
        self.meta: Dict[str, Any] = {}
        game.reset(settings)
        self.settings = settings or {}


class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, GameSession] = {}
        self._lock = threading.Lock()

    def create(self, game_id: Optional[str], game_kind: str, mode: str = "ai",
               settings: Optional[Dict[str, Any]] = None,
               model_id: Optional[str] = None,
               ai_side: int = 1, ai_level: int = 1) -> GameSession:
        factory = GAME_FACTORY.get(game_kind)
        if factory is None:
            raise GameError(f"未知棋种: {game_kind}")
        if not game_id:
            game_id = f"{game_kind}_{int(time.time() * 1000)}"
        with self._lock:
            sess = GameSession(game_id, factory(), mode, settings)
            sess.model_id = model_id
            sess.ai_side = ai_side
            sess.ai_level = ai_level
            self._sessions[game_id] = sess
            return sess

    def get(self, game_id: str) -> GameSession:
        with self._lock:
            sess = self._sessions.get(game_id)
        if sess is None:
            raise GameError(f"对局不存在: {game_id}")
        return sess

    def delete(self, game_id: str) -> None:
        with self._lock:
            self._sessions.pop(game_id, None)

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            items = [
                {
                    "id": s.id,
                    "game": s.game.GAME_ID,
                    "mode": s.mode,
                    "createdAt": s.created_at,
                }
                for s in self._sessions.values()
            ]
        return items

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()


# ---------------------------------------------------------------------------
# 工厂
# ---------------------------------------------------------------------------

GAME_FACTORY: Dict[str, Callable[[], GameBase]] = {}


def register_game(cls: type) -> type:
    GAME_FACTORY[cls.GAME_ID] = cls
    return cls


def create_game(game_kind: str) -> GameBase:
    factory = GAME_FACTORY.get(game_kind)
    if factory is None:
        raise GameError(f"未知棋种: {game_kind}")
    return factory()
