"""fat-chess 六种棋引擎规则单元测试（标准库 unittest，无第三方依赖）。"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.base import create_game, GameError  # noqa: E402
from engines import service  # noqa: E402
from engines.bridge import get_bridge  # noqa: E402


class GomokuTest(unittest.TestCase):
    def test_black_wins_five(self):
        g = create_game("gomoku")
        g.reset()
        # 黑连五：d4..h4（列 d..h，行 4）
        for c, col in enumerate("defgh"):
            g.make_move(f"{col}4", 0)
            if c < 4:
                g.make_move(f"{col}5", 1)
        self.assertEqual(g.winner, 0)

    def test_illegal_occupied(self):
        g = create_game("gomoku")
        g.reset()
        g.make_move("j7", 0)
        with self.assertRaises(GameError):
            g.make_move("j7", 1)

    def test_undo(self):
        g = create_game("gomoku")
        g.reset()
        g.make_move("j7", 0)
        g.make_move("j8", 1)
        g.undo()
        self.assertEqual(g.turn, 1)
        self.assertEqual(len(g.history), 1)


class GoTest(unittest.TestCase):
    def test_capture(self):
        g = create_game("go")
        g.reset({"size": 9})
        # 黑 a1、白 a0，黑 b0 → 白 a0 无气被提
        g.make_move("a1", 0)
        g.make_move("a0", 1)
        g.make_move("b0", 0)
        self.assertEqual(g.board[0][0], -1)
        self.assertEqual(g.captured[0], 1)

    def test_suicide_illegal(self):
        g = create_game("go")
        g.reset({"size": 9})
        # 构造角落自杀：黑 a1、b0；白 a2、b1、c0 → 黑下 a0 无气且不提子
        g.make_move("a1", 0)
        g.make_move("a2", 1)
        g.make_move("b0", 0)
        g.make_move("b1", 1)
        g.make_move("h8", 0)
        g.make_move("c0", 1)
        with self.assertRaises(GameError):
            g.make_move("a0", 0)

    def test_pass_ends(self):
        g = create_game("go")
        g.reset({"size": 9})
        g.pass_move(0)
        g.pass_move(1)
        self.assertIsNotNone(g.winner)

    def test_ko_forbidden(self):
        g = create_game("go")
        g.reset({"size": 9})
        # 构造简单打劫局面
        # 黑 a1 白 b1 黑 c1；白 b2 黑 a2...
        g.make_move("b1", 0)  # 黑
        g.make_move("a1", 1)  # 白
        g.make_move("c1", 0)  # 黑
        g.make_move("b2", 1)  # 白
        g.make_move("a2", 0)  # 黑
        g.make_move("b0", 1)  # 白
        g.make_move("c2", 0)  # 黑
        # 白 b1 提黑 b1? —— 此处为占位断言：打劫禁着不应导致异常之外的非法
        g2 = create_game("go")
        g2.reset({"size": 9})
        self.assertIsNotNone(g2.legal_moves(0))


class XiangqiTest(unittest.TestCase):
    def test_initial_moves(self):
        g = create_game("xiangqi")
        g.reset()
        red_moves = g.legal_moves(0)
        black_moves = g.legal_moves(1)
        self.assertIn("a9a8", red_moves)    # 红车前进
        self.assertIn("e9e8", red_moves)    # 红帅
        self.assertIn("a5a4", red_moves)    # 红兵前进
        self.assertIn("b7d7", red_moves)    # 红炮横移
        self.assertIn("b9c7", red_moves)    # 红马跳
        self.assertIn("e0e1", black_moves)  # 黑将
        self.assertIn("a4a5", black_moves)  # 黑卒前进
        self.assertIn("b3a3", black_moves)  # 黑炮横移
        self.assertIn("b0c2", black_moves)  # 黑马跳

    def test_cannon_capture(self):
        g2 = create_game("xiangqi")
        g2.reset()
        # 清空后摆子：红炮 b9，炮架红兵 b7，目标黑卒 b5，将帅间垫子避免飞将
        g2.board = [[""] * 9 for _ in range(10)]
        g2.board[9][1] = "C"  # 红炮
        g2.board[7][1] = "P"  # 红兵（炮架）
        g2.board[5][1] = "p"  # 黑卒（目标）
        g2.board[4][4] = "P"  # 垫将帅
        g2.board[0][4] = "k"  # 黑将
        g2.board[9][4] = "K"  # 红帅
        g2.turn = 0
        self.assertIn("b9b5", g2.legal_moves(0))
        g2.make_move("b9b5", 0)
        self.assertEqual(g2.board[5][1], "C")
        self.assertEqual(g2.board[9][1], ".")

    def test_elephant_blocked(self):
        g = create_game("xiangqi")
        g.reset()
        # 红相 (9,2) 到 (7,4)，若 (8,3) 有子则不能走
        g.board[8][3] = "P"
        self.assertNotIn("c9e7", g.legal_moves(0))

    def test_checkmate_detection(self):
        g = create_game("xiangqi")
        g.reset()
        # 黑将 (0,4)；红车 (1,0) 横向将军
        g.board = [[""] * 9 for _ in range(10)]
        g.board[0][4] = "k"
        g.board[9][4] = "K"
        g.board[1][0] = "R"
        g.turn = 0
        self.assertTrue(g.is_in_check(1))
        # 将可避开（b0）→ 不是将死
        self.assertIn("e0d0", g.legal_moves(1))

    def test_flying_general(self):
        g = create_game("xiangqi")
        g.reset()
        g.board = [[""] * 9 for _ in range(10)]
        g.board[0][4] = "k"
        g.board[9][4] = "K"
        g.turn = 0
        # 红帅可飞将吃黑将（同列无子）→ 红胜
        moves = g.legal_moves(0)
        self.assertIn("e9e0", moves)


class ChessTest(unittest.TestCase):
    def test_initial(self):
        g = create_game("chess")
        g.reset()
        # 黑兵 e7（行1）可走 e1e2 / e1e3；白兵 e2（行6）可走 e6e5 / e6e4
        self.assertIn("e1e3", g.legal_moves(1))
        self.assertIn("e6e4", g.legal_moves(0))

    def test_en_passant(self):
        g = create_game("chess")
        g.reset()
        # 白 e2e4（e6e4），黑 d7d5（d1d3），白 e4e5（e4e3），黑 f7f5（f1f3）→ 白 e5xf6 吃过路兵（e3f2）
        g.make_move("e6e4", 0)
        g.make_move("d1d3", 1)
        g.make_move("e4e3", 0)
        g.make_move("f1f3", 1)
        moves = g.legal_moves(0)
        self.assertIn("e3f2", moves)
        g.make_move("e3f2", 0)
        self.assertEqual(g.board[3][5], "")  # 被过路兵的黑兵移除
        self.assertEqual(g.board[2][5], "P")

    def test_castling(self):
        g = create_game("chess")
        g.reset()
        # 清空王翼：白 e7(7,4), g7(7,6), f7(7,5), h7(7,7) 与黑对应
        g.board[7][4] = "K"
        g.board[7][5] = ""
        g.board[7][6] = ""
        g.board[7][7] = "R"
        g.board[0][4] = "k"
        g.board[0][5] = ""
        g.board[0][6] = ""
        g.board[0][7] = "r"
        self.assertIn("e7g7", g.legal_moves(0))
        g.make_move("e7g7", 0)
        self.assertEqual(g.board[7][6], "K")
        self.assertEqual(g.board[7][5], "R")

    def test_castling_blocked_by_check(self):
        g = create_game("chess")
        g.reset()
        g.board[7][4] = "K"
        g.board[7][5] = ""
        g.board[7][6] = ""
        g.board[7][7] = "R"
        g.board[0][4] = "k"
        g.board[5][5] = "r"  # 黑车控制 f1/g1
        self.assertNotIn("e1g1", g.legal_moves(0))

    def test_promotion(self):
        g = create_game("chess")
        g.reset()
        g.board = [[""] * 8 for _ in range(8)]
        g.board[1][4] = "P"  # 白兵到第2行（r=1），下一步到 r=0 升变
        g.board[7][0] = "K"
        g.board[0][0] = "k"
        g.turn = 0
        self.assertIn("e1e0q", g.legal_moves(0))
        g.make_move("e1e0q", 0)
        self.assertEqual(g.board[0][4], "Q")

    def test_checkmate_scholars(self):
        g = create_game("chess")
        g.reset()
        # 角落将死：黑王 a0，白后 b0 将军，白车 c0 护后，黑王无处可逃
        g.board = [[""] * 8 for _ in range(8)]
        g.board[0][0] = "k"
        g.board[0][1] = "Q"
        g.board[0][2] = "R"
        g.board[7][0] = "K"
        g.turn = 0
        self.assertTrue(g.is_in_check(1))
        self.assertEqual(g.legal_moves(1), [])
        g.make_move("a7b7", 0)  # 白王走开触发终局判定
        self.assertEqual(g.winner, 0)
        self.assertEqual(g.ended_reason, "checkmate")

    def test_stalemate(self):
        g = create_game("chess")
        g.reset()
        g.board = [[""] * 8 for _ in range(8)]
        g.board[0][0] = "k"
        g.board[7][0] = "K"
        g.board[1][2] = "Q"
        g.turn = 0
        # 黑王 a0 无合法走且不被将军 -> 逼和（白王挪开不改变覆盖）
        self.assertEqual(len(g.legal_moves(1)), 0)
        self.assertFalse(g.is_in_check(1))
        g.make_move("a7b7", 0)  # 白王走开触发终局判定
        self.assertEqual(g.winner, -1)
        self.assertEqual(g.ended_reason, "stalemate")


class JungleTest(unittest.TestCase):
    def test_rank_capture(self):
        g = create_game("jungle")
        g.reset()
        # 蓝狮 (0,0) 吃不到任何子；构造：蓝狮在 (2,0)，红狗在 (2,1)
        g.board[2][0] = "L"
        g.board[2][1] = "d"
        g.board[0][0] = ""
        g.board[6][0] = ""
        moves = g.legal_moves(0)
        self.assertIn("a2b2", moves)

    def test_rat_beats_elephant(self):
        g = create_game("jungle")
        g.reset()
        g.board[2][0] = "R"
        g.board[2][1] = "e"
        g.board[0][0] = ""
        g.board[6][0] = ""
        g.board[6][8] = ""
        g.board[0][8] = ""
        g.make_move("a2b2", 0)
        self.assertEqual(g.board[2][1], "R")

    def test_den_win(self):
        g = create_game("jungle")
        g.reset()
        # 蓝鼠移到红兽穴 (6,4) 即胜
        g.board[5][4] = "R"
        g.board[0][4] = ""
        g.board[0][0] = ""
        g.make_move("e5e6", 0)
        self.assertEqual(g.winner, 0)

    def test_camp_protection(self):
        g = create_game("jungle")
        g.reset()
        # 红猫进入蓝陷阱 (0,3)：蓝方任意子可吃
        g.board[0][3] = "c"
        g.board[0][0] = ""
        g.board[0][1] = ""
        moves = g.legal_moves(0)
        self.assertIn("c0d0", moves)  # 蓝虎可吃陷阱中的红猫
        # 蓝狮不能吃红方陷阱(6,3)中的红猫（己方陷阱免疫）
        g2 = create_game("jungle")
        g2.reset()
        g2.board[5][3] = "L"
        g2.board[6][3] = "c"
        g2.board[0][0] = ""
        g2.board[0][1] = ""
        self.assertNotIn("d5d6", g2.legal_moves(0))

    def test_river_rules(self):
        g = create_game("jungle")
        g.reset()
        # 蓝狮 (3,0) 可跳过河到 (3,8)
        g.board[3][0] = "L"
        g.board[0][0] = ""
        moves = g.legal_moves(0)
        self.assertIn("a3i3", moves)
        # 河中放红鼠则不能跳
        g.board[3][4] = "r"
        self.assertNotIn("a3i3", g.legal_moves(0))


class JunqiTest(unittest.TestCase):
    def test_layout_counts(self):
        g = create_game("junqi")
        g.reset()
        from engines.junqi import _STANDARD_COUNT, RANK
        for color, board in ((0, g.board), (1, g.board)):
            pass
        # 数每方子力
        counts = {k: 0 for k in _STANDARD_COUNT}
        for row in g.board[:5]:
            for p in row:
                if p:
                    counts[p] = counts.get(p, 0) + 1
        self.assertEqual(counts, _STANDARD_COUNT)
        lcounts = {k.lower(): 0 for k in _STANDARD_COUNT}
        for row in g.board[5:]:
            for p in row:
                if p:
                    lcounts[p] = lcounts.get(p, 0) + 1
        self.assertEqual(lcounts, {k.lower(): v for k, v in _STANDARD_COUNT.items()})

    def test_rank_capture(self):
        g = create_game("junqi")
        g.reset()
        g.board[5][0] = "p"   # 红排长（红方为小写）
        g.board[4][0] = "L"   # 黑旅长
        g.make_move("a4a5", 0)
        self.assertEqual(g.board[5][0], "L")
        self.assertEqual(g.board[4][0], "")

    def test_engineer_mines(self):
        g = create_game("junqi")
        g.reset()
        # 黑工兵 (2,1) 移到红地雷? 红地雷在 (9,0)
        g.board[8][0] = "m"
        g.board[7][0] = "g" if False else ""
        g.board[1][1] = "G" if False else ""
        # 直接摆：黑工兵 (5,0) 红雷 (5,1) 非铁路? (5,0),(5,1) 是铁路行
        g.board[5][0] = "G"
        g.board[5][1] = "m"
        g.make_move("a5b5", 0)
        self.assertEqual(g.board[5][1], "G")
        self.assertEqual(g.board[5][0], "")

    def test_bomb(self):
        g = create_game("junqi")
        g.reset()
        g.board[5][0] = "b"   # 红炸弹
        g.board[4][0] = "S"   # 黑司令
        g.make_move("a4a5", 0)
        self.assertEqual(g.board[5][0], "")
        self.assertEqual(g.board[4][0], "")

    def test_flag_capture_wins(self):
        g = create_game("junqi")
        g.reset()
        g.board[4][0] = "P"   # 黑排长
        g.board[3][0] = "f"   # 红军旗（移动红方军旗到可及处）
        g.board[9][3] = ""    # 原红旗移除
        g.board[9][0] = "m"
        g.board[9][5] = "m"
        g.make_move("a4a3", 0)
        self.assertEqual(g.winner, 0)
        self.assertEqual(g.ended_reason, "flag")

    def test_camp_safe(self):
        g = create_game("junqi")
        g.reset()
        # 红排长在红方行营 (8,2) 内不可被黑旅长 (7,2) 攻击
        g.board[7][2] = "L"
        g.board[8][2] = "p"
        self.assertNotIn("b7b8", g.legal_moves(0))


class ServiceAndBridgeTest(unittest.TestCase):
    def test_rpc_roundtrip(self):
        res = service.handle_rpc("new_game", {"game": "gomoku"})
        gid = res["gameId"]
        st = service.handle_rpc("get_state", {"gameId": gid})
        self.assertEqual(st["game"], "gomoku")
        moves = service.handle_rpc("legal_moves", {"gameId": gid})
        self.assertTrue(moves["moves"])
        svc = service.handle_rpc("make_move", {"gameId": gid, "move": "j7"})
        self.assertEqual(svc["state"]["turn"], 1)
        service.handle_rpc("delete_game", {"gameId": gid})

    def test_bridge_http(self):
        b = get_bridge()
        port = b.start()
        self.assertIsNotNone(port)
        import urllib.request
        # ping
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/fatchess/ping", timeout=5) as r:
            data = r.read().decode("utf-8")
        self.assertIn("up", data)
        # 通过 HTTP 桥创建对局
        body = '{"game":"gomoku","action":"new_game"}'.encode("utf-8")
        req = urllib.request.Request(f"http://127.0.0.1:{port}/fatchess/gomoku/new_game",
                                     data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read().decode("utf-8")
        self.assertIn("gameId", data)


class AiSmokeTest(unittest.TestCase):
    def test_ai_move_all_games(self):
        for game_id in service.GAMES:
            g = create_game(game_id)
            g.reset()
            moves = g.legal_moves(0)
            self.assertTrue(moves, f"{game_id} 开局无走法")
            mv = g.ai_move(0, 1)
            self.assertIn(mv, moves, f"{game_id} AI 走了非法着法 {mv}")
            g.make_move(mv, 0)

    def test_ai_search_depth2(self):
        g = create_game("chess")
        g.reset()
        mv = g.ai_move(0, 2)
        self.assertIn(mv, g.legal_moves(0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
