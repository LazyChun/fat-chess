"""
本地 AI 引擎：统一的 alpha-beta 极小极大搜索 + 各棋种静态评估。

难度 level：
- 1：贪心（深度 1）
- 2：深度 2（含 alpha-beta）
- 3：深度 3（复杂棋种自动降为 2）

每个棋种提供 evaluate(game, side) -> 以 side 视角的分数。
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from .base import create_game
from .jungle import DENS as _JUNGLE_DENS

INF = 10 ** 9

# 深度 >= 3 时，非根节点只展开按贪心排序后的前 N 个候选，
# 把大师级的搜索复杂度控制在可接受范围（约 根*N^(depth-1)）。
_SEARCH_WIDTH = 6

# ---------------------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------------------


def _clone(game) -> Any:
    g = create_game(game.GAME_ID)
    g.reset(dict(getattr(game, "settings", None) or {}))
    for h in game.history:
        g.apply_move(h["move"], g.turn)
    return g


def _eval(game, side: int) -> float:
    fn = _EVALUATORS.get(game.GAME_ID)
    if fn is None:
        return 0.0
    return fn(game, side)


def _search(game, depth: int, alpha: float, beta: float, side: int,
            width: Optional[int] = None) -> float:
    if game.winner is not None:
        if game.winner == -1:
            return 0.0
        return INF if game.winner == side else -INF
    if depth <= 0:
        return _eval(game, side)

    moves = game.legal_moves(side)
    if not moves:
        # 无子可走：将军则负，否则和棋
        try:
            chk = game.is_in_check(side)
        except AttributeError:
            chk = False
        return -INF + 1 if chk else 0.0

    # 吃子优先排序
    def _mv_score(m: str) -> int:
        if len(m) >= 4:
            try:
                tr = int(m[3:4])
                tc = ord(m[2:3]) - ord("a")
                tgt = game.board[tr][tc]
            except Exception:
                return 0
            return 100 if tgt else 0
        return 0

    moves.sort(key=_mv_score, reverse=True)
    if width is not None and len(moves) > width:
        moves = moves[:width]

    best = -INF
    for m in moves:
        g2 = _clone(game)
        g2.make_move(m, side)
        val = -_search(g2, depth - 1, -beta, -alpha, 1 - side, width)
        if val > best:
            best = val
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    return best


def pick_move(game, moves: List[str], side: int, level: int = 1) -> str:
    if not moves:
        raise ValueError("无棋可走")
    level = max(1, min(3, int(level or 1)))
    depth_map = {
        "gomoku": {1: 1, 2: 2, 3: 3},
        "go": {1: 0, 2: 0, 3: 0},          # 围棋用分级启发式，不走搜索
        "xiangqi": {1: 1, 2: 2, 3: 3},
        "chess": {1: 1, 2: 2, 3: 3},
        "jungle": {1: 1, 2: 2, 3: 3},
        "junqi": {1: 1, 2: 2, 3: 3},
    }
    dmap = depth_map.get(game.GAME_ID, {1: 1, 2: 2, 3: 3})
    depth = dmap.get(level, 1)

    if game.GAME_ID == "go":
        return _go_heuristic(game, moves, side, level)

    if depth <= 1 or len(moves) == 1:
        scored = [(m, _search(_clone_and_move(game, m, side), 0, -INF, INF, side))
                  for m in moves]
        scored.sort(key=lambda x: -x[1])
        if level <= 1 and len(scored) > 1:
            # 入门：只在前 40% 候选中随机，会做出欠考虑的走法
            k = max(2, int(len(scored) * 0.4))
            return random.choice([m for m, _ in scored[:k]])
        best_score = scored[0][1]
        best = [m for m, s in scored if s == best_score]
        return random.choice(best)

    best_moves = []
    best_val = -INF
    alpha = -INF
    # 大师（depth>=3）：深层剪枝，只展开排序后的前 N 个候选
    width = _SEARCH_WIDTH if depth >= 3 else None
    for m in moves:
        g2 = _clone_and_move(game, m, side)
        val = -_search(g2, depth - 1, -INF, -alpha, 1 - side, width)
        if val > best_val:
            best_val = val
            best_moves = [m]
        elif val == best_val:
            best_moves.append(m)
        alpha = max(alpha, best_val)
    return random.choice(best_moves)


def _clone_and_move(game, move: str, side: int) -> Any:
    g2 = _clone(game)
    g2.make_move(move, side)
    return g2


def _go_heuristic(game, moves: List[str], side: int, level: int) -> str:
    """围棋分级启发式：
    - 入门：启发式打分 + 随机扰动（在前 1/3 候选中随机，容易漏算）
    - 进阶：确定性启发式（提子 > 保气 > 占角星位）
    - 大师：在前 16 个启发式候选上做 1 层搜索，按子力/气/提子评估择优
    """
    def score(m):
        s = 0
        r = ord(m[0]) - ord("a")
        c = int(m[1:])
        # 提子优先
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < game.size and 0 <= nc < game.size and game.board[nr][nc] == 1 - side:
                _, libs = game._group(nr, nc)
                if len(libs) == 1:
                    s += 1000
                elif len(libs) == 2:
                    s += 200
        # 自方气的扩展
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < game.size and 0 <= nc < game.size and game.board[nr][nc] == side:
                s += 30
        # 靠近边角星位
        mid = game.size // 2
        s += (15 - abs(r - mid) - abs(c - mid)) * 2
        return s

    scored = [(m, score(m)) for m in moves]
    scored.sort(key=lambda x: -x[1])

    if level <= 1:
        k = max(1, len(scored) // 3)
        return random.choice([m for m, _ in scored[:k]])

    if level >= 3:
        best_m, best_v = scored[0][0], -INF
        for m, _ in scored[:16]:
            g2 = _clone_and_move(game, m, side)
            v = _go_eval(g2, side)
            if v > best_v:
                best_v, best_m = v, m
        return best_m

    return scored[0][0]


# ---------------------------------------------------------------------------
# 静态评估
# ---------------------------------------------------------------------------

def _gomoku_eval(game, side: int) -> float:
    n = game.size
    dirs = ((1, 0), (0, 1), (1, 1), (1, -1))
    total = 0.0

    def line_score(r, c, dr, dc, color):
        # 统计以该点为端点的连续长度与开放度
        cnt = 1
        open_end = 0
        rr, cc = r + dr, c + dc
        while 0 <= rr < n and 0 <= cc < n and game.board[rr][cc] == color:
            cnt += 1
            rr += dr
            cc += dc
        if 0 <= rr < n and 0 <= cc < n and game.board[rr][cc] == -1:
            open_end += 1
        rr, cc = r - dr, c - dc
        while 0 <= rr < n and 0 <= cc < n and game.board[rr][cc] == color:
            cnt += 1
            rr -= dr
            cc -= dc
        if 0 <= rr < n and 0 <= cc < n and game.board[rr][cc] == -1:
            open_end += 1
        return cnt, open_end

    weights = {1: 10, 2: 60, 3: 500, 4: 6000, 5: 100000}
    for r in range(n):
        for c in range(n):
            color = game.board[r][c]
            if color == -1:
                continue
            sign = 1 if color == side else -1
            for dr, dc in dirs:
                cnt, open_end = line_score(r, c, dr, dc, color)
                w = weights.get(cnt, 100000)
                if cnt >= 5:
                    w = 100000
                elif open_end == 2:
                    w *= 2
                total += sign * w
    return total


def _go_eval(game, side: int) -> float:
    score = 0.0
    for r in range(game.size):
        for c in range(game.size):
            v = game.board[r][c]
            if v == -1:
                continue
            sign = 1 if v == side else -1
            _, libs = game._group(r, c)
            score += sign * (8 + len(libs) * 3)
    # 提子差
    cap = game.captured
    score += (cap[side] - cap[1 - side]) * 60
    return score


_XQ_VALUE = {"K": 10000, "A": 120, "B": 120, "N": 400, "R": 900, "C": 450, "P": 100}
_CH_VALUE = {"k": 10000, "q": 900, "r": 500, "b": 330, "n": 320, "p": 100}


def _xiangqi_eval(game, side: int) -> float:
    score = 0.0
    for r in range(game.rows):
        for c in range(game.cols):
            p = game.board[r][c]
            if not p or p == ".":
                continue
            color = 0 if p.isupper() else 1
            sign = 1 if color == side else -1
            v = _XQ_VALUE.get(p.upper(), 0)
            if p.lower() == "p":
                # 过河兵价值更高
                crossed = r < 5 if color == 0 else r >= 5
                v = 180 if crossed else 100
            score += sign * v
    return score


def _chess_eval(game, side: int) -> float:
    score = 0.0
    for r in range(8):
        for c in range(8):
            p = game.board[r][c]
            if not p:
                continue
            color = 0 if p.isupper() else 1
            sign = 1 if color == side else -1
            v = _CH_VALUE.get(p.lower(), 0)
            # 中心控制加成
            center = (4 - max(abs(r - 3.5), abs(c - 3.5)))
            v += max(0, center) * 2 if p.lower() in ("n", "b", "q") else 0
            score += sign * v
    # 子力数量惩罚（鼓励吃子）
    return score


_JUNGLE_VALUE = {"E": 8, "L": 7, "T": 6, "P": 5, "W": 4, "D": 3, "C": 2, "R": 1}


def _jungle_eval(game, side: int) -> float:
    score = 0.0
    den = _JUNGLE_DENS[1 - side]  # 对方兽穴
    for r in range(game.rows):
        for c in range(game.cols):
            p = game.board[r][c]
            if not p or p == ".":
                continue
            color = 0 if p.isupper() else 1
            sign = 1 if color == side else -1
            v = _JUNGLE_VALUE.get(p.upper(), 0) * 100
            # 距离对方兽穴越近越有价值（进攻导向）
            dist = abs(r - den[0]) + abs(c - den[1])
            v += max(0, (8 - dist)) * 8
            score += sign * v
    return score


_JUNQI_VALUE = {"S": 9, "J": 8, "Z": 7, "L": 6, "T": 5, "Y": 4, "C": 3, "P": 2, "G": 1}


def _junqi_eval(game, side: int) -> float:
    score = 0.0
    for r in range(game.rows):
        for c in range(game.cols):
            p = game.board[r][c]
            if not p:
                continue
            color = 0 if p.isupper() else 1
            sign = 1 if color == side else -1
            low = p.lower()
            if low in ("f", "m"):
                continue  # 军旗地雷不计子力（军旗被吃直接负）
            v = _JUNQI_VALUE.get(p.upper(), 0) * 100
            score += sign * v
    return score


_EVALUATORS = {
    "gomoku": _gomoku_eval,
    "go": _go_eval,
    "xiangqi": _xiangqi_eval,
    "chess": _chess_eval,
    "jungle": _jungle_eval,
    "junqi": _junqi_eval,
}
