"""
军棋（明盘·陆战棋）9x10。本实现为明盘变体（双方布局公开可见），规则：

- 军衔：司令>军长>师长>旅长>团长>营长>连长>排长>工兵；同归于尽；工兵可挖地雷；
  炸弹可炸任何子（同归于尽）。
- 地雷、军旗不可移动；军旗被吃即负；吃光对方棋子也胜。
- 行营（安全营）内棋子不能被攻击；大本营内棋子不可移动。
- 铁路（第 2-7 行）上走直线任意格，不可越子；工兵可越子，且可拐一次直角。
- 非铁路区域每步一格。
坐标 a0..i9，走法 "fromto"；大写=黑方，小写=红方。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .base import GameBase, GameError, parse_square, sq_text, register_game

ROWS, COLS = 10, 9
RANK = {"S": 9, "J": 8, "Z": 7, "L": 6, "T": 5, "Y": 4, "C": 3, "P": 2, "G": 1}
PIECE_NAMES = {"S": "司令", "J": "军长", "Z": "师长", "L": "旅长", "T": "团长",
               "Y": "营长", "C": "连长", "P": "排长", "G": "工兵", "M": "地雷",
               "B": "炸弹", "F": "军旗"}

FORTS = {0: [(0, 3), (0, 5)], 1: [(9, 3), (9, 5)]}
CAMPS = {0: [(1, 2), (1, 4), (1, 6)], 1: [(8, 2), (8, 4), (8, 6)]}
RAILWAY_ROWS = set(range(2, 8))

_BLACK_LAYOUT = {
    (0, 0): "M", (0, 3): "F", (0, 5): "M", (0, 8): "M",
    (1, 1): "G", (1, 3): "J", (1, 5): "G", (1, 7): "Y",
    (2, 0): "P", (2, 1): "G", (2, 2): "C", (2, 4): "S", (2, 6): "P", (2, 8): "C",
    (3, 1): "T", (3, 2): "C", (3, 3): "B", (3, 5): "Y", (3, 7): "B",
    (4, 0): "L", (4, 2): "T", (4, 4): "L", (4, 5): "Z", (4, 6): "Z", (4, 8): "P",
}

_STANDARD_COUNT = {"S": 1, "J": 1, "Z": 2, "L": 2, "T": 2, "Y": 2, "C": 3, "P": 3, "G": 3, "M": 3, "B": 2, "F": 1}


def _mirror(pos: Tuple[int, int]) -> Tuple[int, int]:
    return (ROWS - 1 - pos[0], pos[1])


@register_game
class Junqi(GameBase):
    GAME_ID = "junqi"
    NAME = "军棋（明盘）"
    SETTINGS = ("first", "open")

    def reset(self, settings: Optional[Dict[str, Any]] = None) -> None:
        self.settings = dict(settings or {})
        self.rows = ROWS
        self.cols = COLS
        self.board = [[""] * COLS for _ in range(ROWS)]
        for pos, p in _BLACK_LAYOUT.items():
            self.board[pos[0]][pos[1]] = p
        for pos, p in _BLACK_LAYOUT.items():
            r, c = _mirror(pos)
            self.board[r][c] = p.lower()
        self.turn = 0
        self.winner = None
        self.ended_reason = ""
        self.history = []
        self.last_move: Optional[str] = None
        self.move_count = 0

    def _side_of(self, p: str) -> int:
        return 0 if p.isupper() else 1

    def _in_fort(self, r: int, c: int, side: int) -> bool:
        return (r, c) in FORTS[side]

    def _in_own_camp(self, r: int, c: int, side: int) -> bool:
        return (r, c) in CAMPS[side]

    # -- 走法 --
    def _add(self, moves, r, c, nr, nc, side) -> None:
        if not (0 <= nr < ROWS and 0 <= nc < COLS):
            return
        tgt = self.board[nr][nc]
        if tgt and self._side_of(tgt) == side:
            return
        moves.append((r, c, nr, nc))

    def _moves_for(self, r: int, c: int, p: str, side: int,
                   moves: List[Tuple[int, int, int, int]]) -> None:
        if self._in_fort(r, c, side):
            return  # 大本营内不可移动
        if p.lower() in ("m", "f"):
            return  # 地雷/军旗不可移动
        on_rail = r in RAILWAY_ROWS
        if on_rail:
            if p.lower() == "g":
                self._engineer_moves(r, c, side, moves)
            else:
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    while 0 <= nr < ROWS and 0 <= nc < COLS:
                        tgt = self.board[nr][nc]
                        if tgt:
                            if self._side_of(tgt) != side:
                                moves.append((r, c, nr, nc))
                            break
                        moves.append((r, c, nr, nc))
                        nr += dr
                        nc += dc
        else:
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                self._add(moves, r, c, r + dr, c + dc, side)

    def _engineer_moves(self, r: int, c: int, side: int,
                        moves: List[Tuple[int, int, int, int]]) -> None:
        """工兵铁路走法：任意直线可越子，可拐一次直角（BFS ≤2 次转向）。"""
        # 先收集直线可达点（可越子）
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            while 0 <= nr < ROWS and 0 <= nc < COLS:
                self._add(moves, r, c, nr, nc, side)
                nr += dr
                nc += dc
        # 拐一次：在交叉点换向
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cr, cc = r + dr, c + dc
            while 0 <= cr < ROWS and 0 <= cc < COLS:
                # cr,cc 为换向点（可达，可越子）
                for dr2, dc2 in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if (dr2, dc2) == (dr, dc) or (dr2, dc2) == (-dr, -dc):
                        continue
                    nr, nc = cr + dr2, cc + dc2
                    while 0 <= nr < ROWS and 0 <= nc < COLS:
                        self._add(moves, r, c, nr, nc, side)
                        nr += dr2
                        nc += dc2
                cr += dr
                cc += dc

    def _pseudo_moves(self, side: int) -> List[Tuple[int, int, int, int]]:
        out = []
        for r in range(ROWS):
            for c in range(COLS):
                p = self.board[r][c]
                if p and self._side_of(p) == side:
                    self._moves_for(r, c, p, side, out)
        return out

    def legal_moves(self, side: int) -> List[str]:
        out = []
        for r, c, nr, nc in self._pseudo_moves(side):
            tgt = self.board[nr][nc]
            if not tgt or self._can_capture(self.board[r][c], tgt, nr, nc):
                out.append(sq_text(r, c) + sq_text(nr, nc))
        return out

    def _can_capture(self, attacker: str, target: str, tr: int, tc: int) -> bool:
        side = self._side_of(attacker)
        tside = self._side_of(target)
        # 目标在自己行营内不可被攻击
        if self._in_own_camp(tr, tc, tside):
            return False
        al, tl = attacker.lower(), target.lower()
        if tl == "f":
            return True  # 扛军旗
        if al == "b" or tl == "b":
            return True  # 炸弹同归于尽
        if tl == "m":
            return al == "g" or al == "b"  # 工兵挖雷/炸弹炸雷
        if al == "g" and tl != "m":
            # 工兵吃非雷子：工兵最小，只能吃工兵（同级同归于尽）
            return False if RANK[target.upper()] > 1 else True
        return RANK[attacker.upper()] >= RANK[target.upper()]

    def apply_move(self, move: str, side: int) -> None:
        if len(move) < 4:
            raise GameError(f"非法走法: {move}")
        r, c = parse_square(move[:2])
        nr, nc = parse_square(move[2:4])
        p = self.board[r][c]
        if not p or self._side_of(p) != side:
            raise GameError(f"该位置没有己方棋子: {move[:2]}")
        if move not in self.legal_moves(side):
            raise GameError(f"非法走法: {move}")
        tgt = self.board[nr][nc]
        if tgt and not self._can_capture(p, tgt, nr, nc):
            raise GameError(f"不能吃掉对方 {PIECE_NAMES.get(tgt.upper(), tgt)}: {move}")
        captured = tgt
        if tgt:
            if captured.lower() == "b" or p.lower() == "b":
                self.board[r][c] = ""
                self.board[nr][nc] = ""
                outcome = "bomb"
            else:
                self.board[nr][nc] = p
                self.board[r][c] = ""
                outcome = "capture"
        else:
            self.board[nr][nc] = p
            self.board[r][c] = ""
            outcome = "move"
        self.last_move = move
        self.move_count += 1
        self.history.append({"move": move, "side": side, "captured": captured,
                             "outcome": outcome})
        # 胜负
        if captured and captured.lower() == "f":
            self.winner = side
            self.ended_reason = "flag"
            return
        opp = 1 - side
        if not any(self._side_of(x) == opp for row in self.board for x in row):
            self.winner = side
            self.ended_reason = "no_pieces"
            return
        if self.move_count >= 300:
            self.winner = -1
            self.ended_reason = "move_limit"
            return
        self.turn = opp

    def state(self) -> Dict[str, Any]:
        return {
            "rows": ROWS,
            "cols": COLS,
            "board": self.board,
            "turn": self.turn,
            "winner": self.winner,
            "endedReason": self.ended_reason,
            "lastMove": self.last_move,
            "forts": FORTS,
            "camps": CAMPS,
            "railwayRows": sorted(RAILWAY_ROWS),
            "history": [h["move"] for h in self.history],
        }

    def to_text(self) -> str:
        header = "   " + " ".join(chr(ord("a") + c) for c in range(COLS))
        lines = [header]
        for r in range(ROWS):
            row = " ".join(self.board[r][c] if self.board[r][c] else "." for c in range(COLS))
            lines.append(f"{r:2d} {row}")
        lines.append("大写=黑方，小写=红方；走法 fromto；军旗被吃即负")
        return "\n".join(lines)
