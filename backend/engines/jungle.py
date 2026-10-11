"""
斗兽棋（Jungle / 暗棋·斗兽）7x9。规则：
- 象>狮>虎>豹>狼>狗>猫>鼠；鼠吃象（鼠在陆地上可吃象）。
- 陷阱：进入对方陷阱的棋子可被对方任意棋吃；己方陷阱中的棋子不能被吃。
- 兽穴：不能进入己方兽穴；进入对方兽穴即胜；吃光对方棋子也胜。
- 河流：仅鼠可入水；狮、虎可沿直线跳过河（途中有鼠则不能跳）。
坐标 a0..i6，走法 "fromto"。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .base import GameBase, GameError, parse_square, sq_text, register_game

ROWS, COLS = 7, 9
RANK = {"E": 8, "L": 7, "T": 6, "P": 5, "W": 4, "D": 3, "C": 2, "R": 1}
PIECE_NAMES = {"E": "象", "L": "狮", "T": "虎", "P": "豹", "W": "狼", "D": "狗", "C": "猫", "R": "鼠"}

DENS = {0: (0, 4), 1: (6, 4)}
TRAPS = {0: [(0, 3), (0, 5), (1, 4)], 1: [(6, 3), (6, 5), (5, 4)]}
RIVER = {(3, c) for c in range(1, 8)}


@register_game
class Jungle(GameBase):
    GAME_ID = "jungle"
    NAME = "斗兽棋"
    SETTINGS = ("first",)

    _INIT = [
        list("ELTP.WDCR"),
        list("........."),
        list("........."),
        list("........."),
        list("........."),
        list("........."),
        list("RWCD.PTLE"),
    ]

    def reset(self, settings: Optional[Dict[str, Any]] = None) -> None:
        self.settings = dict(settings or {})
        self.board = [list(row) for row in self._INIT]
        self.rows = ROWS
        self.cols = COLS
        self.turn = 0
        self.winner = None
        self.ended_reason = ""
        self.history = []
        self.last_move: Optional[str] = None
        self.move_count = 0

    def _side_of(self, p: str) -> int:
        return 0 if p.isupper() else 1

    def _own_piece(self, p: str, side: int) -> bool:
        return p not in (".", "", None) and self._side_of(p) == side

    # -- 走法 --
    def _add(self, moves, r, c, nr, nc, side) -> None:
        if not (0 <= nr < ROWS and 0 <= nc < COLS):
            return
        if (nr, nc) == DENS[side]:
            return  # 不能进己方兽穴
        tgt = self.board[nr][nc]
        if tgt not in (".", "", None) and self._side_of(tgt) == side:
            return
        moves.append((r, c, nr, nc))

    def _moves_for(self, r: int, c: int, p: str, side: int,
                   moves: List[Tuple[int, int, int, int]]) -> None:
        low = p.lower()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if low == "r":
                self._add(moves, r, c, nr, nc, side)  # 鼠：可入水
                continue
            if (nr, nc) in RIVER:
                continue  # 非鼠不入水
            self._add(moves, r, c, nr, nc, side)
        # 狮/虎跳河：沿直线跳过水域到下一块陆地
        if low in ("l", "t"):
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                jumped = False
                while 0 <= nr < ROWS and 0 <= nc < COLS:
                    if (nr, nc) in RIVER:
                        if self.board[nr][nc] not in (".", "", None):
                            break  # 河中有鼠阻挡
                        jumped = True
                    else:
                        if jumped:
                            self._add(moves, r, c, nr, nc, side)
                        break
                    nr += dr
                    nc += dc

    def _pseudo_moves(self, side: int) -> List[Tuple[int, int, int, int]]:
        out = []
        for r in range(ROWS):
            for c in range(COLS):
                p = self.board[r][c]
                if p not in (".", "", None) and self._side_of(p) == side:
                    self._moves_for(r, c, p, side, out)
        return out

    def legal_moves(self, side: int) -> List[str]:
        out = []
        for r, c, nr, nc in self._pseudo_moves(side):
            tgt = self.board[nr][nc]
            if tgt in ("", ".", None) or self._can_capture(self.board[r][c], tgt, nr, nc):
                out.append(sq_text(r, c) + sq_text(nr, nc))
        return out

    def _can_capture(self, attacker: str, target: str, tr: int, tc: int) -> bool:
        if self._side_of(attacker) == self._side_of(target):
            return False
        side = self._side_of(attacker)
        # 目标在己方陷阱：不能吃
        if (tr, tc) in TRAPS[self._side_of(target)]:
            return False
        # 目标在对方陷阱：任意可吃
        if (tr, tc) in TRAPS[side]:
            return True
        # 鼠吃象
        if attacker.lower() == "r" and target.lower() == "e":
            # 鼠在水中不能吃陆地象
            return True
        # 象不吃鼠
        if attacker.lower() == "e" and target.lower() == "r":
            return False
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
        if tgt not in (".", "", None) and not self._can_capture(p, tgt, nr, nc):
            raise GameError(f"不能吃掉对方 {PIECE_NAMES.get(tgt.upper(), tgt)}: {move}")
        captured = "" if tgt in (".", "", None) else tgt
        self.board[nr][nc] = p
        self.board[r][c] = ""
        self.last_move = move
        self.move_count += 1
        self.history.append({"move": move, "side": side, "captured": captured})
        # 胜负
        if (nr, nc) == DENS[1 - side]:
            self.winner = side
            self.ended_reason = "den"
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
            "dens": DENS,
            "traps": TRAPS,
            "river": sorted(RIVER),
            "history": [h["move"] for h in self.history],
        }

    def to_text(self) -> str:
        header = "   " + " ".join(chr(ord("a") + c) for c in range(COLS))
        lines = [header]
        for r in range(ROWS):
            row = " ".join(self.board[r][c] if self.board[r][c] else "." for c in range(COLS))
            lines.append(f"{r:2d} {row}")
        lines.append("大写=蓝方，小写=红方；象>狮>虎>豹>狼>狗>猫>鼠，鼠吃象；走法 fromto")
        return "\n".join(lines)
