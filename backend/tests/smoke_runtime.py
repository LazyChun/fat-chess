"""
fat-chess 插件后端运行时冒烟测试（非 unittest，直接运行）：
1. 以子进程启动 backend/main.py（JSON-RPC over stdin/stdout）
2. 通过 RPC 开新局、列走法、走子、AI 走子
3. 通过 HTTP 桥（/fatchess/ping 与 make_move）验证 MCP 回调链路
4. 验证 new_game 返回 mode/aiSide/modelId 等字段（前端依赖）

运行：python tests/smoke_runtime.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = os.path.join(BACKEND_DIR, "main.py")

FAILED = []


def check(name: str, cond: bool, extra: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}{('  ' + extra) if extra else ''}")
    if not cond:
        FAILED.append(name)


def main() -> int:
    env = dict(os.environ)
    env["FAT_NOTES_PLUGIN_HOST_URL"] = "http://127.0.0.1:8022"
    env["FAT_NOTES_PLUGIN_ID"] = "99a32860-fe62-4c3c-9bc9-56943bbd83dd"
    env["PYTHONIOENCODING"] = "utf-8"

    proc = subprocess.Popen(
        [sys.executable, "-u", MAIN],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=BACKEND_DIR,
        bufsize=1,
    )

    def send(handler: str, params: dict, req_id: str = "r1") -> dict:
        assert proc.stdin is not None and proc.stdout is not None
        proc.stdin.write(json.dumps({"id": req_id, "handler": handler, "params": params}) + "\n")
        proc.stdin.flush()
        while True:
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError("后端进程退出（stdout 关闭）")
            try:
                resp = json.loads(line)
            except json.JSONDecodeError:
                continue
            if resp.get("id") == req_id or resp.get("status") == "ready":
                return resp

    try:
        # 1. ready 握手（首行即 ready 状态）
        ready = send("__ping__", {})
        check("ready 握手", ready.get("status") in ("ready", "success"),
              f"status={ready.get('status')} handlers={ready.get('handlers')}")

        # 2. 桥信息
        bridge = send("fatchess_bridge_info", {}, "bridge")
        check("桥信息", bridge.get("status") == "success")
        result = bridge.get("result") or {}
        port = result.get("port")
        check("桥端口有效", isinstance(port, int) and port > 0, f"port={port}")
        check("桥已启动", result.get("started") is True)

        # 3. 新建中国象棋（人机模式，AI 后手）
        ng = send("fatchess_rpc", {"action": "new_game", "game": "xiangqi",
                                   "mode": "ai", "aiLevel": 2, "modelId": None}, "ng")
        check("new_game 成功", ng.get("status") == "success")
        ngd = ng.get("result") or {}
        game_id = ngd.get("gameId")
        check("new_game 返回 gameId", bool(game_id))
        check("new_game 返回 mode=ai", ngd.get("mode") == "ai", f"mode={ngd.get('mode')}")
        check("new_game 返回 aiSide=1", ngd.get("aiSide") == 1, f"aiSide={ngd.get('aiSide')}")
        check("new_game 返回 aiLevel=2", ngd.get("aiLevel") == 2, f"aiLevel={ngd.get('aiLevel')}")
        st = ngd.get("state") or {}
        check("state 含 board/turn", "board" in st and "turn" in st)
        check("先手为红方(0)", st.get("turn") == 0, f"turn={st.get('turn')}")

        # 4. 列走法（红方）
        lm = send("fatchess_rpc", {"action": "legal_moves", "gameId": game_id}, "lm")
        moves = (lm.get("result") or {}).get("moves") or []
        check("红方有合法走法", len(moves) > 20, f"count={len(moves)}")
        check("红马 b9c7 合法", "b9c7" in moves)

        # 5. 红方走子 b9c7（红马跳）
        mv = send("fatchess_rpc", {"action": "make_move", "gameId": game_id, "move": "b9c7"}, "mv")
        check("make_move 成功", mv.get("status") == "success")
        mvst = (mv.get("result") or {}).get("state") or {}
        check("走子后轮到黑方", mvst.get("turn") == 1, f"turn={mvst.get('turn')}")

        # 6. AI 走子（此时轮到黑方）
        ai = send("fatchess_rpc", {"action": "ai_move", "gameId": game_id}, "ai")
        check("ai_move 成功", ai.get("status") == "success")
        aist = (ai.get("result") or {}).get("state") or {}
        check("AI 走子后轮到红方", aist.get("turn") == 0, f"turn={aist.get('turn')}")

        # 7. HTTP 桥：ping
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/fatchess/ping", timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        check("HTTP 桥 ping", body.get("ok") is True and body.get("status") == "up", str(body))

        # 8. HTTP 桥：红方走子（等价于大模型工具回调；红相 c9a7）
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/fatchess/xiangqi/make_move",
            data=json.dumps({"gameId": game_id, "move": "c9a7"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        check("HTTP 桥 make_move ok", body.get("ok") is True, str(body)[:120])
        httst = (body.get("data") or {}).get("state") or {}
        check("HTTP 桥走子后轮到黑方", httst.get("turn") == 1, f"turn={httst.get('turn')}")

        # 9. 悔棋（红方一步）
        un = send("fatchess_rpc", {"action": "undo", "gameId": game_id}, "un")
        check("undo 成功", un.get("status") == "success")

        # 10. 错误路径：非法走法
        bad = send("fatchess_rpc", {"action": "make_move", "gameId": game_id, "move": "z9z0"}, "bad")
        check("非法走法报错", bad.get("status") == "error", str(bad.get("error"))[:80])

        # 11. 五子棋桥新建（LLM 模式，验证 modelId 透传）
        ng2 = send("fatchess_rpc", {"action": "new_game", "game": "gomoku",
                                    "mode": "llm", "modelId": "test-model"}, "ng2")
        ng2d = ng2.get("result") or {}
        check("llm 模式 new_game", ng2.get("status") == "success")
        check("llm 模式 modelId 透传", ng2d.get("modelId") == "test-model",
              f"modelId={ng2d.get('modelId')}")
        check("llm 模式 state 15x15", len(ng2d.get("state", {}).get("board", [])) == 15)

        # 12. 列出对局
        lg = send("fatchess_rpc", {"action": "list_games", "gameId": game_id}, "lg")
        check("list_games", lg.get("status") == "success" and len(lg.get("result", {}).get("games", [])) >= 2)

    finally:
        try:
            send("__shutdown__", {}, "quit")
        except Exception:
            pass
        time.sleep(0.3)
        try:
            proc.kill()
        except Exception:
            pass

    print("-" * 40)
    if FAILED:
        print(f"冒烟测试失败 {len(FAILED)} 项: {FAILED}")
        return 1
    print("冒烟测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
