"""
五子棋（Gomoku）15x15。黑先手，五连（含长连）即胜。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import GameBase, GameError, parse_square, sq_text, register_game

SIZE = 15
DIRS = [(1, 0), (0, 1), (1, 1), (1, -1)]


@register_game
class Gomoku(GameBase):
    GAME_ID = "gomoku"
    NAME = "五子棋"
    SETTINGS = ("size", "first")

    def reset(self, settings: Optional[Dict[str, Any]] = None) -> None:
        self.settings = dict(settings or {})
        self.size = SIZE
        self.board = [[-1] * SIZE for _ in range(SIZE)]
        self.turn = 0
        self.winner = None
        self.ended_reason = ""
        self.history = []
        self.last_move: Optional[str] = None

    # -- 规则 --
    def legal_moves(self, side: int) -> List[str]:
        out = []
        for r in range(SIZE):
            for c in range(SIZE):
                if self.board[r][c] == -1:
                    out.append(sq_text(r, c))
        return out

    def _count(self, r: int, c: int, dr: int, dc: int, color: int) -> int:
        n = 0
        rr, cc = r, c
        while 0 <= rr < SIZE and 0 <= cc < SIZE and self.board[rr][cc] == color:
            n += 1
            rr += dr
            cc += dc
        return n

    def _check_win(self, r: int, c: int) -> bool:
        color = self.board[r][c]
        for dr, dc in DIRS:
            if self._count(r, c, dr, dc, color) + self._count(r, c, -dr, -dc, color) - 1 >= 5:
                return True
        return False

    def apply_move(self, move: str, side: int) -> None:
        r, c = parse_square(move)
        if not (0 <= r < SIZE and 0 <= c < SIZE):
            raise GameError(f"越界: {move}")
        if self.board[r][c] != -1:
            raise GameError(f"该点已有棋子: {move}")
        self.board[r][c] = side
        self.last_move = move
        if self._check_win(r, c):
            self.winner = side
            self.ended_reason = "five"
        elif not any(v == -1 for row in self.board for v in row):
            self.winner = -1
            self.ended_reason = "draw"
        else:
            self.turn = 1 - side
        self.history.append({"move": move, "side": side})

    # -- 状态 --
    def state(self) -> Dict[str, Any]:
        return {
            "size": SIZE,
            "board": self.board,          # -1 空, 0 黑, 1 白
            "turn": self.turn,
            "winner": self.winner,
            "endedReason": self.ended_reason,
            "lastMove": self.last_move,
            "history": [h["move"] for h in self.history],
        }

    def to_text(self) -> str:
        symbol = {-1: ".", 0: "X", 1: "O"}
        lines = ["   " + " ".join(chr(ord("a") + c) for c in range(SIZE))]
        for r in range(SIZE):
            row = "".join(symbol[self.board[r][c]] for c in range(SIZE))
            lines.append(f"{r:2d} {row}")
        lines.append("X=黑(先手) O=白")
        return "\n".join(lines)
