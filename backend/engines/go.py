"""
围棋（Go）9/13/19 路。规则：
- 落子后无气即提子；己方落子后无气且不能提子为自杀（禁着）。
- 简单打劫：采用位置超劫（positional superko）——回到历史出现过完全相同盘面的着法非法。
- 双方连续虚着（pass）则终局，按"子 + 领地"近似数空。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .base import GameBase, GameError, parse_square, sq_text, register_game

DEFAULT_SIZE = 19
SIZES = (9, 13, 19)
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _board_hash(board: List[List[int]]) -> int:
    h = 0
    for row in board:
        for v in row:
            h = (h * 3 + (v + 1)) & 0xFFFFFFFF
    return h


@register_game
class Go(GameBase):
    GAME_ID = "go"
    NAME = "围棋"
    SETTINGS = ("size", "handicap", "komi")

    def reset(self, settings: Optional[Dict[str, Any]] = None) -> None:
        self.settings = dict(settings or {})
        try:
            size = int(self.settings.get("size") or DEFAULT_SIZE)
        except (TypeError, ValueError):
            size = DEFAULT_SIZE
        self.size = size if size in SIZES else DEFAULT_SIZE
        self.board = [[-1] * self.size for _ in range(self.size)]
        self.turn = 0
        self.winner = None
        self.ended_reason = ""
        self.history: List[Dict[str, Any]] = []
        self.passes: int = 0
        self.visited: Set[int] = set()
        self.visited.add(_board_hash(self.board))
        self.last_move: Optional[str] = None
        self.captured = [0, 0]
        # 贴目（白方补偿），默认 6.5
        try:
            self.komi = float(self.settings.get("komi") or 6.5)
        except (TypeError, ValueError):
            self.komi = 6.5
        # 让子：黑方预先布子（简化：星位）
        handicap = int(self.settings.get("handicap") or 0)
        if handicap and size >= 9:
            self._place_handicap(handicap)

    def _place_handicap(self, n: int) -> None:
        if self.size == 9:
            stars = [(2, 2), (6, 6), (2, 6), (6, 2)]
        else:
            s = 3 if self.size == 19 else 2
            e = self.size - 1 - s
            mid = self.size // 2
            stars = [(s, s), (e, e), (s, e), (e, s)]
            if self.size >= 13:
                stars += [(mid, s), (mid, e), (s, mid), (e, mid), (mid, mid)]
        for r, c in stars[:n]:
            self.board[r][c] = 0
        self.turn = 1  # 让子后白先

    # -- 气与提子 --
    def _group(self, r: int, c: int) -> Tuple[List[Tuple[int, int]], Set[Tuple[int, int]]]:
        color = self.board[r][c]
        if color == -1:
            return [], set()
        stack = [(r, c)]
        seen = {(r, c)}
        liberties: Set[Tuple[int, int]] = set()
        while stack:
            cr, cc = stack.pop()
            for dr, dc in DIRS:
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < self.size and 0 <= nc < self.size):
                    continue
                v = self.board[nr][nc]
                if v == -1:
                    liberties.add((nr, nc))
                elif v == color and (nr, nc) not in seen:
                    seen.add((nr, nc))
                    stack.append((nr, nc))
        return list(seen), liberties

    def legal_moves(self, side: int) -> List[str]:
        out = []
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == -1 and self._is_legal(r, c, side):
                    out.append(sq_text(r, c))
        return out

    def _is_legal(self, r: int, c: int, side: int) -> bool:
        board = [row[:] for row in self.board]
        board[r][c] = side
        # 提掉对方无气棋
        opp = 1 - side
        removed = 0
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size and board[nr][nc] == opp:
                _, libs = self._group_xy(board, nr, nc)
                if not libs:
                    removed += self._remove_group(board, nr, nc)
        # 己方无气？
        _, libs = self._group_xy(board, r, c)
        if not libs:
            return False
        # 超劫
        h = _board_hash(board)
        if h in self.visited:
            return False
        return True

    @staticmethod
    def _group_xy(board: List[List[int]], r: int, c: int) -> Tuple[List[Tuple[int, int]], Set[Tuple[int, int]]]:
        n = len(board)
        color = board[r][c]
        stack = [(r, c)]
        seen = {(r, c)}
        libs: Set[Tuple[int, int]] = set()
        while stack:
            cr, cc = stack.pop()
            for dr, dc in DIRS:
                nr, nc = cr + dr, cc + dc
                if not (0 <= nr < n and 0 <= nc < n):
                    continue
                v = board[nr][nc]
                if v == -1:
                    libs.add((nr, nc))
                elif v == color and (nr, nc) not in seen:
                    seen.add((nr, nc))
                    stack.append((nr, nc))
        return list(seen), libs

    @staticmethod
    def _remove_group(board: List[List[int]], r: int, c: int) -> int:
        n = len(board)
        color = board[r][c]
        stack = [(r, c)]
        removed = 0
        while stack:
            cr, cc = stack.pop()
            if board[cr][cc] != color:
                continue
            board[cr][cc] = -1
            removed += 1
            for dr, dc in DIRS:
                nr, nc = cr + dr, cc + dc
                if 0 <= nr < n and 0 <= nc < n and board[nr][nc] == color:
                    stack.append((nr, nc))
        return removed

    def apply_move(self, move: str, side: int) -> None:
        if move == "pass":
            self.passes += 1
            self.last_move = None
            if self.passes >= 2:
                self._score_game()
            else:
                self.turn = 1 - side
            self.history.append({"move": "pass", "side": side})
            return
        self.passes = 0
        r, c = parse_square(move)
        if not (0 <= r < self.size and 0 <= c < self.size):
            raise GameError(f"越界: {move}")
        if self.board[r][c] != -1:
            raise GameError(f"该点已有棋子: {move}")
        if not self._is_legal(r, c, side):
            raise GameError(f"禁着点（自杀或劫）: {move}")
        # 落子并提子
        self.board[r][c] = side
        opp = 1 - side
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size and self.board[nr][nc] == opp:
                _, libs = self._group(nr, nc)
                if not libs:
                    removed = self._remove_group(self.board, nr, nc)
                    self.captured[side] += removed
        self.visited.add(_board_hash(self.board))
        self.last_move = move
        self.history.append({"move": move, "side": side})
        self.turn = 1 - side

    def pass_move(self, side: int) -> Dict[str, Any]:
        return self.make_move("pass", side)

    # -- 终局数空（近似：子 + 被一方完全包围的空点） --
    def _score_game(self) -> None:
        n = self.size
        territory = [[-1] * n for _ in range(n)]  # -1 未定, 0/1 归属
        for r in range(n):
            for c in range(n):
                if self.board[r][c] != -1 or territory[r][c] != -1:
                    continue
                # flood fill 找空区
                stack = [(r, c)]
                region: List[Tuple[int, int]] = []
                borders = set()
                seen = {(r, c)}
                while stack:
                    cr, cc = stack.pop()
                    region.append((cr, cc))
                    for dr, dc in DIRS:
                        nr, nc = cr + dr, cc + dc
                        if not (0 <= nr < n and 0 <= nc < n):
                            continue
                        v = self.board[nr][nc]
                        if v == -1:
                            if (nr, nc) not in seen:
                                seen.add((nr, nc))
                                stack.append((nr, nc))
                        else:
                            borders.add(v)
                owner = -1
                if len(borders) == 1:
                    owner = next(iter(borders))
                for (rr, cc) in region:
                    territory[rr][cc] = owner
        black = sum(1 for row in self.board for v in row if v == 0)
        white = sum(1 for row in self.board for v in row if v == 1)
        black += sum(1 for row in territory for v in row if v == 0)
        white += sum(1 for row in territory for v in row if v == 1)
        white += self.komi
        black_disp = round(black - self.komi, 1)
        white_disp = round(white, 1)
        self.score = {"black": black_disp, "white": white_disp}
        if black > white:
            self.winner = 0
            self.ended_reason = "score"
            self.score["winner"] = 0
        elif white > black:
            self.winner = 1
            self.ended_reason = "score"
            self.score["winner"] = 1
        else:
            self.winner = -1
            self.ended_reason = "draw"
            self.score["winner"] = -1

    def state(self) -> Dict[str, Any]:
        return {
            "size": self.size,
            "board": self.board,
            "turn": self.turn,
            "winner": self.winner,
            "endedReason": self.ended_reason,
            "lastMove": self.last_move,
            "passes": self.passes,
            "captured": self.captured,
            "komi": self.komi,
            "score": getattr(self, "score", None),
            "history": [h["move"] for h in self.history],
        }

    def to_text(self) -> str:
        n = self.size
        symbol = {-1: ".", 0: "X", 1: "O"}
        header = "   " + " ".join(chr(ord("a") + c) for c in range(n))
        lines = [header]
        for r in range(n):
            lines.append(f"{r:2d} " + " ".join(symbol[self.board[r][c]] for c in range(n)))
        lines.append("X=黑(先手) O=白  pass 表示虚着，连续两次虚着终局")
        return "\n".join(lines)
