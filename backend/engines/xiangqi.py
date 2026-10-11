"""
中国象棋（Xiangqi）9x10。规则完整：
- 将/帅限九宫，仕/士限九宫斜行，相/象限本方且塞象眼，马蹩马腿，炮隔子吃，
  兵/卒过河后可横走，将帅不能照面（飞将）。
- 被将军时必须应将；无子可走（被将死或困毙）判负。
走法格式 "fromto"，如红马 "b0c2"。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .base import GameBase, GameError, parse_square, sq_text, register_game

ROWS, COLS = 10, 9

# 红子大写，黑子小写
RED_PIECES = "KABNRCP"
BLACK_PIECES = "kabnrcp"
RED = 0
BLACK = 1


def _is_red(p: str) -> bool:
    return p in RED_PIECES


def _is_black(p: str) -> bool:
    return p in BLACK_PIECES


def _empty(p) -> bool:
    return p in (".", "", None)


def _side_of(p: str) -> int:
    return RED if _is_red(p) else BLACK


def _in_palace(r: int, c: int, side: int) -> bool:
    if side == RED:
        return 7 <= r <= 9 and 3 <= c <= 5
    return 0 <= r <= 2 and 3 <= c <= 5


def _own_side(r: int, c: int, side: int) -> bool:
    if side == RED:
        return r >= 5
    return r <= 4


@register_game
class Xiangqi(GameBase):
    GAME_ID = "xiangqi"
    NAME = "中国象棋"
    SETTINGS = ("first",)

    _INIT = [
        list("rnbakabnr"),
        list("........."),
        list("........."),
        list(".c.....c."),
        list("p.p.p.p.p"),
        list("P.P.P.P.P"),
        list("........."),
        list(".C.....C."),
        list("........."),
        list("RNBAKABNR"),
    ]

    def reset(self, settings: Optional[Dict[str, Any]] = None) -> None:
        self.settings = dict(settings or {})
        self.board = [list(row) for row in self._INIT]
        self.rows = ROWS
        self.cols = COLS
        self.turn = RED
        self.winner = None
        self.ended_reason = ""
        self.history = []
        self.last_move: Optional[str] = None
        self.in_check = [False, False]

    # -- 走法生成 --
    def _find_general(self, side: int) -> Optional[Tuple[int, int]]:
        target = "K" if side == RED else "k"
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] == target:
                    return r, c
        return None

    def _pseudo_moves(self, side: int) -> List[Tuple[int, int, int, int]]:
        moves: List[Tuple[int, int, int, int]] = []
        for r in range(ROWS):
            for c in range(COLS):
                p = self.board[r][c]
                if _empty(p) or _side_of(p) != side:
                    continue
                self._moves_for(r, c, p, side, moves)
        return moves

    def _moves_for(self, r: int, c: int, p: str, side: int,
                   moves: List[Tuple[int, int, int, int]]) -> None:
        def add(nr: int, nc: int) -> None:
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                tgt = self.board[nr][nc]
                if _empty(tgt) or _side_of(tgt) != side:
                    moves.append((r, c, nr, nc))

        up = -1 if side == RED else 1  # 前进方向（红向上，黑向下）
        if p in "Kk":  # 将/帅
            for dr, dc in ((up, 0), (-up, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if _in_palace(nr, nc, side):
                    add(nr, nc)
            # 飞将：与对方将同列且中间无子
            opp = "k" if side == RED else "K"
            for nr in range(r + up, ROWS if up > 0 else -1, up):
                if not (0 <= nr < ROWS):
                    break
                piece = self.board[nr][c]
                if not _empty(piece):
                    if piece == opp:
                        moves.append((r, c, nr, c))
                    break
        elif p in "Aa":  # 仕/士
            for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                nr, nc = r + dr, c + dc
                if _in_palace(nr, nc, side):
                    add(nr, nc)
        elif p in "Bb":  # 相/象
            for dr, dc in ((-2, -2), (-2, 2), (2, -2), (2, 2)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < ROWS and 0 <= nc < COLS and _own_side(nr, nc, side):
                    mid_r, mid_c = r + dr // 2, c + dc // 2
                    if _empty(self.board[mid_r][mid_c]):
                        add(nr, nc)
        elif p in "Nn":  # 马
            for dr, dc in ((-2, -1), (-2, 1), (2, -1), (2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < ROWS and 0 <= nc < COLS:
                    leg_r, leg_c = r + (1 if abs(dr) == 2 else 0) * (dr // abs(dr) if dr else 0), \
                                    c + (1 if abs(dc) == 2 else 0) * (dc // abs(dc) if dc else 0)
                    # 蹩马腿点
                    if abs(dr) == 2:
                        leg_r, leg_c = r + dr // 2, c
                    else:
                        leg_r, leg_c = r, c + dc // 2
                    if _empty(self.board[leg_r][leg_c]):
                        add(nr, nc)
        elif p in "Rr":  # 车
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                while 0 <= nr < ROWS and 0 <= nc < COLS:
                    tgt = self.board[nr][nc]
                    if _empty(tgt):
                        moves.append((r, c, nr, nc))
                    else:
                        if _side_of(tgt) != side:
                            moves.append((r, c, nr, nc))
                        break
                    nr += dr
                    nc += dc
        elif p in "Cc":  # 炮
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                jumped = False
                while 0 <= nr < ROWS and 0 <= nc < COLS:
                    tgt = self.board[nr][nc]
                    if not jumped:
                        if _empty(tgt):
                            moves.append((r, c, nr, nc))
                        else:
                            jumped = True
                    else:
                        if not _empty(tgt):
                            if _side_of(tgt) != side:
                                moves.append((r, c, nr, nc))
                            break
                    nr += dr
                    nc += dc
        elif p in "Pp":  # 兵/卒
            crossed = r < 5 if side == RED else r >= 5
            add(r + up, c)
            if crossed:
                add(r, c + 1)
                add(r, c - 1)

    # -- 将军判定 --
    def _attacks(self, r: int, c: int, target: Tuple[int, int]) -> bool:
        """判断 (r,c) 的棋子是否能攻击 target 点（含马腿/炮架/飞将逻辑）。"""
        p = self.board[r][c]
        tr, tc = target
        if p in "Kk":
            dr, dc = tr - r, tc - c
            if abs(dr) + abs(dc) == 1:
                return True
            if dc == 0:  # 飞将：同列且中间无子
                lo, hi = sorted((r, tr))
                for rr in range(lo + 1, hi):
                    if not _empty(self.board[rr][c]):
                        return False
                return True
            return False
        if p in "Aa":
            return abs(tr - r) == 1 and abs(tc - c) == 1
        if p in "Bb":
            return abs(tr - r) == 2 and abs(tc - c) == 2 and \
                _own_side(tr, tc, _side_of(p)) and _empty(self.board[(r + tr) // 2][(c + tc) // 2])
        if p in "Nn":
            dr, dc = tr - r, tc - c
            if abs(dr) * abs(dc) != 2:
                return False
            if abs(dr) == 2:
                leg = (r + dr // 2, c)
            else:
                leg = (r, c + dc // 2)
            return _empty(self.board[leg[0]][leg[1]])
        if p in "Rr":
            if r == tr:
                lo, hi = sorted((c, tc))
                for cc in range(lo + 1, hi):
                    if not _empty(self.board[r][cc]):
                        return False
                return True
            if c == tc:
                lo, hi = sorted((r, tr))
                for rr in range(lo + 1, hi):
                    if not _empty(self.board[rr][c]):
                        return False
                return True
            return False
        if p in "Cc":
            if r == tr:
                lo, hi = sorted((c, tc))
                mid = [self.board[r][cc] for cc in range(lo + 1, hi) if not _empty(self.board[r][cc])]
                return len(mid) == 1
            if c == tc:
                lo, hi = sorted((r, tr))
                mid = [self.board[rr][c] for rr in range(lo + 1, hi) if not _empty(self.board[rr][c])]
                return len(mid) == 1
            return False
        if p in "Pp":
            dr, dc = tr - r, tc - c
            up = -1 if _side_of(p) == RED else 1
            crossed = r < 5 if _side_of(p) == RED else r >= 5
            if dr == up and dc == 0:
                return True
            if crossed and dr == 0 and abs(dc) == 1:
                return True
            return False
        return False

    def is_in_check(self, side: int) -> bool:
        g = self._find_general(side)
        if g is None:
            return True
        opp = 1 - side
        for r in range(ROWS):
            for c in range(COLS):
                p = self.board[r][c]
                if not _empty(p) and _side_of(p) == opp and self._attacks(r, c, g):
                    return True
        return False

    def legal_moves(self, side: int) -> List[str]:
        out: List[str] = []
        for r, c, nr, nc in self._pseudo_moves(side):
            if self._safe(r, c, nr, nc, side):
                out.append(sq_text(r, c) + sq_text(nr, nc))
        return out

    def _safe(self, r: int, c: int, nr: int, nc: int, side: int) -> bool:
        saved = self.board[nr][nc]
        self.board[nr][nc] = self.board[r][c]
        self.board[r][c] = "."
        ok = not self.is_in_check(side)
        self.board[r][c] = self.board[nr][nc]
        self.board[nr][nc] = saved
        return ok

    def apply_move(self, move: str, side: int) -> None:
        if len(move) < 4:
            raise GameError(f"非法走法: {move}")
        r, c = parse_square(move[:2])
        nr, nc = parse_square(move[2:4])
        if not (0 <= r < ROWS and 0 <= c < COLS and 0 <= nr < ROWS and 0 <= nc < COLS):
            raise GameError(f"越界: {move}")
        p = self.board[r][c]
        if _empty(p) or _side_of(p) != side:
            raise GameError(f"该位置没有己方棋子: {move[:2]}")
        tgt = self.board[nr][nc]
        if not _empty(tgt) and _side_of(tgt) == side:
            raise GameError(f"不能吃己方棋子: {move}")
        if move not in self.legal_moves(side):
            raise GameError(f"非法走法: {move}")
        captured = self.board[nr][nc]
        self.board[nr][nc] = p
        self.board[r][c] = "."
        self.last_move = move
        self.history.append({"move": move, "side": side, "captured": captured})
        self.turn = 1 - side
        # 胜负
        opp = 1 - side
        if self.is_in_check(opp) and not self.legal_moves(opp):
            self.winner = side
            self.ended_reason = "checkmate"
        elif not self.legal_moves(opp):
            # 困毙：无子可走（即使不被将军）同样判负
            self.winner = side
            self.ended_reason = "stalemate"
        self.in_check = [self.is_in_check(RED), self.is_in_check(BLACK)]

    def state(self) -> Dict[str, Any]:
        return {
            "rows": ROWS,
            "cols": COLS,
            "board": self.board,
            "turn": self.turn,
            "winner": self.winner,
            "endedReason": self.ended_reason,
            "lastMove": self.last_move,
            "inCheck": self.in_check,
            "history": [h["move"] for h in self.history],
        }

    def to_text(self) -> str:
        names = {"K": "帅", "A": "仕", "B": "相", "N": "马", "R": "车", "C": "炮", "P": "兵",
                 "k": "将", "a": "士", "b": "象", "n": "马", "r": "车", "c": "炮", "p": "卒"}
        header = "   " + " ".join(chr(ord("a") + c) for c in range(COLS))
        lines = [header]
        for r in range(ROWS):
            row = " ".join(names.get(self.board[r][c], ".") for c in range(COLS))
            if r in (4, 5):
                row = row.replace(" ", " ", 1)
            lines.append(f"{r:2d} {row}")
        lines.append("大写=红方，小写=黑方；走法格式如 b0c2（从->到）")
        return "\n".join(lines)
