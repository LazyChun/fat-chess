"""
国际象棋（Chess）8x8。规则完整：
- 王车易位（含权利与通路判定）、吃过路兵、兵升变、将军、将死、逼和（无子可走）。
- 附：50 回合规则与三次重复判和。
坐标 a0..h7（0 行 = 第 8 横线 = 黑方底线），走法 UCI 风格 "e2e4"、"e7e8q"。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .base import GameBase, GameError, parse_square, sq_text, register_game

N = 8
WHITE, BLACK = 0, 1
# 行 0 = 第 8 横线（黑方底线），白方在行 7（第 1 横线）

_INIT_BACK = ["r", "n", "b", "q", "k", "b", "n", "r"]
_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def fen_to_board(fen: str) -> List[List[str]]:
    rows = fen.split(" ")[0].split("/")
    board = []
    for row in rows:
        line: List[str] = []
        for ch in row:
            if ch.isdigit():
                line.extend([""] * int(ch))
            else:
                line.append(ch)
        board.append(line)
    return board


@register_game
class Chess(GameBase):
    GAME_ID = "chess"
    NAME = "国际象棋"
    SETTINGS = ("first",)

    def reset(self, settings: Optional[Dict[str, Any]] = None) -> None:
        self.settings = dict(settings or {})
        self.board = fen_to_board(_START_FEN)
        self.turn = WHITE
        self.winner = None
        self.ended_reason = ""
        self.history: List[Dict[str, Any]] = []
        self.castling = {"K": True, "Q": True, "k": True, "q": True}
        self.ep_target: Optional[Tuple[int, int]] = None  # 可被吃过路兵的格子
        self.halfmove = 0
        self.fullmove = 1
        self.position_count: Dict[str, int] = {}
        self.last_move: Optional[str] = None
        self._note_position()

    def _board_key(self) -> str:
        rows = []
        for r in range(N):
            line = ""
            empty = 0
            for c in range(N):
                p = self.board[r][c]
                if p:
                    if empty:
                        line += str(empty)
                        empty = 0
                    line += p
                else:
                    empty += 1
            if empty:
                line += str(empty)
            rows.append(line)
        return "/".join(rows)

    def _note_position(self) -> None:
        key = self._board_key() + f" {self.turn} {self.castling} {self.ep_target}"
        self.position_count[key] = self.position_count.get(key, 0) + 1

    def to_fen(self) -> str:
        cp = "".join(k for k in ("K", "Q", "k", "q") if self.castling.get(k)) or "-"
        ep = "-"
        if self.ep_target:
            ep = sq_text(*self.ep_target)
        return f"{self._board_key()} {'w' if self.turn == WHITE else 'b'} {cp} {ep} {self.halfmove} {self.fullmove}"

    # -- 走法生成 --
    def _pseudo_moves(self, side: int) -> List[Tuple[Tuple[int, int], Tuple[int, int], str]]:
        moves: List[Tuple[Tuple[int, int], Tuple[int, int], str]] = []
        for r in range(N):
            for c in range(N):
                p = self.board[r][c]
                if not p:
                    continue
                color = WHITE if p.isupper() else BLACK
                if color != side:
                    continue
                self._moves_for(r, c, p, side, moves)
        return moves

    def _add(self, moves, r, c, nr, nc, promo="") -> None:
        if not (0 <= nr < N and 0 <= nc < N):
            return
        tgt = self.board[nr][nc]
        if tgt and ((tgt.isupper() and self.turn == BLACK) or (tgt.islower() and self.turn == WHITE)):
            return  # 吃己方
        if promo:
            for pr in promo:
                moves.append(((r, c), (nr, nc), pr))
        else:
            moves.append(((r, c), (nr, nc), ""))

    def _moves_for(self, r: int, c: int, p: str, side: int,
                   moves: List[Tuple[Tuple[int, int], Tuple[int, int], str]]) -> None:
        low = p.lower()
        if low == "p":
            self._pawn_moves(r, c, side, moves)
        elif low == "n":
            for dr, dc in ((2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)):
                self._add(moves, r, c, r + dr, c + dc)
        elif low == "b":
            for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                nr, nc = r + dr, c + dc
                while 0 <= nr < N and 0 <= nc < N:
                    if not self._add(moves, r, c, nr, nc):
                        break
                    if self.board[nr][nc]:
                        break
                    nr += dr
                    nc += dc
        elif low == "r":
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                while 0 <= nr < N and 0 <= nc < N:
                    if not self._add(moves, r, c, nr, nc):
                        break
                    if self.board[nr][nc]:
                        break
                    nr += dr
                    nc += dc
        elif low == "q":
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nr, nc = r + dr, c + dc
                while 0 <= nr < N and 0 <= nc < N:
                    if not self._add(moves, r, c, nr, nc):
                        break
                    if self.board[nr][nc]:
                        break
                    nr += dr
                    nc += dc
        elif low == "k":
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    self._add(moves, r, c, r + dr, c + dc)
            # 易位
            if side == WHITE and r == 7 and c == 4:
                if self.castling.get("K") and not self.board[7][5] and not self.board[7][6] \
                        and self.board[7][7] == "R":
                    self._add(moves, 7, 4, 7, 6)
                if self.castling.get("Q") and not self.board[7][3] and not self.board[7][2] \
                        and not self.board[7][1] and self.board[7][0] == "R":
                    self._add(moves, 7, 4, 7, 2)
            elif side == BLACK and r == 0 and c == 4:
                if self.castling.get("k") and not self.board[0][5] and not self.board[0][6] \
                        and self.board[0][7] == "r":
                    self._add(moves, 0, 4, 0, 6)
                if self.castling.get("q") and not self.board[0][3] and not self.board[0][2] \
                        and not self.board[0][1] and self.board[0][0] == "r":
                    self._add(moves, 0, 4, 0, 2)

    def _pawn_moves(self, r: int, c: int, side: int,
                    moves: List[Tuple[Tuple[int, int], Tuple[int, int], str]]) -> None:
        promo_row = 0 if side == WHITE else N - 1
        # 白方在行 7，向行 0 前进（dr=-1）；黑方在行 0，向行 7 前进（dr=+1）
        dr = -1 if side == WHITE else 1
        promo = "qnrb" if r + dr == promo_row else ""
        # 直进
        if not self.board[r + dr][c]:
            self._add(moves, r, c, r + dr, c, promo)
            start_row = 6 if side == WHITE else 1
            if r == start_row and not self.board[r + 2 * dr][c]:
                self._add(moves, r, c, r + 2 * dr, c)
        # 斜吃
        for dc in (-1, 1):
            nc = c + dc
            if 0 <= nc < N:
                tgt = self.board[r + dr][nc]
                if tgt and ((side == WHITE and tgt.islower()) or (side == BLACK and tgt.isupper())):
                    self._add(moves, r, c, r + dr, nc, promo)
                # 吃过路兵
                if self.ep_target and self.ep_target == (r + dr, nc):
                    self._add(moves, r, c, r + dr, nc)

    # -- 将军/合法走法 --
    def _find_king(self, side: int) -> Optional[Tuple[int, int]]:
        target = "K" if side == WHITE else "k"
        for r in range(N):
            for c in range(N):
                if self.board[r][c] == target:
                    return r, c
        return None

    def _attacks_square(self, side: int, sq: Tuple[int, int]) -> bool:
        tr, tc = sq
        for r in range(N):
            for c in range(N):
                p = self.board[r][c]
                if not p:
                    continue
                color = WHITE if p.isupper() else BLACK
                if color != side:
                    continue
                if self._piece_attacks(r, c, p, tr, tc):
                    return True
        return False

    def _piece_attacks(self, r: int, c: int, p: str, tr: int, tc: int) -> bool:
        low = p.lower()
        if low == "p":
            dr = -1 if p.isupper() else 1
            return tr == r + dr and abs(tc - c) == 1
        if low == "n":
            return abs(tr - r) * abs(tc - c) == 2
        if low == "k":
            return max(abs(tr - r), abs(tc - c)) == 1
        if low == "b":
            return abs(tr - r) == abs(tc - c) and self._clear_diag(r, c, tr, tc)
        if low == "r":
            return (tr == r or tc == c) and self._clear_line(r, c, tr, tc)
        if low == "q":
            return ((abs(tr - r) == abs(tc - c)) and self._clear_diag(r, c, tr, tc)) or \
                   ((tr == r or tc == c) and self._clear_line(r, c, tr, tc))
        return False

    def _clear_line(self, r, c, tr, tc) -> bool:
        if r == tr:
            lo, hi = sorted((c, tc))
            for cc in range(lo + 1, hi):
                if self.board[r][cc]:
                    return False
            return True
        if c == tc:
            lo, hi = sorted((r, tr))
            for rr in range(lo + 1, hi):
                if self.board[rr][c]:
                    return False
            return True
        return False

    def _clear_diag(self, r, c, tr, tc) -> bool:
        if abs(tr - r) != abs(tc - c):
            return False
        dr = 1 if tr > r else -1
        dc = 1 if tc > c else -1
        rr, cc = r + dr, c + dc
        while rr != tr:
            if self.board[rr][cc]:
                return False
            rr += dr
            cc += dc
        return True

    def is_in_check(self, side: int) -> bool:
        k = self._find_king(side)
        if k is None:
            return True
        return self._attacks_square(1 - side, k)

    def _make_pseudo(self, move, ep=None) -> None:
        (r, c), (nr, nc), promo = move
        moved = self.board[r][c]
        self.board[nr][nc] = moved
        self.board[r][c] = ""
        if promo:
            self.board[nr][nc] = promo.upper() if moved.isupper() else promo.lower()
        # 吃过路兵：斜移到空置的过路兵目标格，吃掉旁边的兵
        ep_t = self.ep_target if ep is None else ep
        if (nr, nc) == ep_t and c != nc:
            self.board[r][nc] = ""
        # 易位车移动
        if moved.lower() == "k" and abs(nc - c) == 2:
            if nc == 6:
                self.board[r][5] = self.board[r][7]
                self.board[r][7] = ""
            else:
                self.board[r][3] = self.board[r][0]
                self.board[r][0] = ""

    def _unmake_pseudo(self, move, saved) -> None:
        (r, c), (nr, nc), _ = move
        # 恢复简单化：对 legal_moves 使用拷贝，不真正需要 unmake
        self.board = saved

    def legal_moves(self, side: int) -> List[str]:
        out: List[str] = []
        for mv in self._pseudo_moves(side):
            saved = [row[:] for row in self.board]
            self._make_pseudo(mv)
            if not self.is_in_check(side):
                out.append(self._move_uci(mv))
            self.board = saved
        return out

    @staticmethod
    def _move_uci(mv) -> str:
        (r, c), (nr, nc), promo = mv
        return sq_text(r, c) + sq_text(nr, nc) + promo

    def apply_move(self, move: str, side: int) -> None:
        if len(move) < 4:
            raise GameError(f"非法走法: {move}")
        r, c = parse_square(move[:2])
        nr, nc = parse_square(move[2:4])
        promo = move[4:5] if len(move) > 4 else ""
        p = self.board[r][c]
        if not p or (side == WHITE) != p.isupper():
            raise GameError(f"该位置没有己方棋子: {move[:2]}")
        if move not in self.legal_moves(side):
            raise GameError(f"非法走法: {move}")
        captured = self.board[nr][nc]
        # 记录易位权利变化
        old_castling = dict(self.castling)
        if p == "K":
            self.castling["K"] = self.castling["Q"] = False
        elif p == "k":
            self.castling["k"] = self.castling["q"] = False
        if p == "R" and r == 7 and c == 0:
            self.castling["Q"] = False
        elif p == "R" and r == 7 and c == 7:
            self.castling["K"] = False
        elif p == "r" and r == 0 and c == 0:
            self.castling["q"] = False
        elif p == "r" and r == 0 and c == 7:
            self.castling["k"] = False
        if captured == "R" and nr == 7 and nc == 0:
            self.castling["Q"] = False
        elif captured == "R" and nr == 7 and nc == 7:
            self.castling["K"] = False
        elif captured == "r" and nr == 0 and nc == 0:
            self.castling["q"] = False
        elif captured == "r" and nr == 0 and nc == 7:
            self.castling["k"] = False

        old_ep = self.ep_target
        self.ep_target = None
        # 双步兵进记录过路兵目标
        if p.lower() == "p" and abs(nr - r) == 2:
            self.ep_target = ((r + nr) // 2, c)

        self._make_pseudo(((r, c), (nr, nc), promo), ep=old_ep)
        self.last_move = move
        if p.lower() == "p" or captured:
            self.halfmove = 0
        else:
            self.halfmove += 1
        if self.turn == BLACK:
            self.fullmove += 1
        self.turn = 1 - side
        self.history.append({
            "move": move, "side": side, "captured": captured,
            "oldCastling": old_castling, "oldEp": old_ep,
        })
        self._note_position()
        self._check_result(side)

    def _check_result(self, mover: int) -> None:
        opp = 1 - mover
        if self.is_in_check(opp):
            if not self.legal_moves(opp):
                self.winner = mover
                self.ended_reason = "checkmate"
                return
        else:
            if not self.legal_moves(opp):
                self.winner = -1
                self.ended_reason = "stalemate"
                return
        # 50 回合
        if self.halfmove >= 100:
            self.winner = -1
            self.ended_reason = "fifty"
            return
        # 三次重复
        if max(self.position_count.values()) >= 3:
            self.winner = -1
            self.ended_reason = "repetition"
            return

    def undo(self) -> Dict[str, Any]:
        if not self.history:
            raise GameError("没有可悔的棋")
        self.history.pop()
        self.reset(self.settings)
        for h in self.history:
            self.apply_move(h["move"], h["side"])
        return self.state()

    def state(self) -> Dict[str, Any]:
        return {
            "size": N,
            "board": self.board,
            "turn": self.turn,
            "winner": self.winner,
            "endedReason": self.ended_reason,
            "lastMove": self.last_move,
            "castling": self.castling,
            "epTarget": sq_text(*self.ep_target) if self.ep_target else None,
            "halfmove": self.halfmove,
            "fen": self.to_fen(),
            "history": [h["move"] for h in self.history],
        }

    def to_text(self) -> str:
        return f"FEN: {self.to_fen()}\n" \
               "大写=白方，小写=黑方；走法 UCI 格式，如 e2e4、e7e8q（升变）。"
