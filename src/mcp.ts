/**
 * MCP 工具注册：把 6 棋种 × 5 动作 = 30 个 requestUrl 工具注册进宿主。
 *
 * 工具 URL 指向插件后端进程内的 HTTP 桥（127.0.0.1:<bridgePort>）。
 * 大模型在 llm_move 流程中通过 sdk.ai.chat(toolIds) 自动调用这些工具落子。
 *
 * 幂等策略：addTool 已存在时报 "already exists"，改走 editTool 刷新 URL，
 * 保证桥端口变化后工具仍指向最新地址。
 */
import type { FatNotesPluginSDK } from "fat-notes-sdk";
import { GAMES, GAME_MAP } from "./games";

const TOOL_PREFIX = "fatchess";
const ACTIONS: Array<{ action: string; name: string; desc: string; params: Array<Record<string, unknown>> }> = [
  {
    action: "new_game",
    name: "开新局",
    desc: "开始一局新的对局。返回 { gameId, state }，state.text 为文字棋盘。",
    params: [],
  },
  {
    action: "get_state",
    name: "查看局面",
    desc: "查看当前局面。返回 { board, turn, winner, text }，text 为文字棋盘。",
    params: [
      { id: "gameId", name: "gameId", dataType: "string", required: true, description: "对局 id", value: "" },
    ],
  },
  {
    action: "legal_moves",
    name: "列出合法走法",
    desc: "列出某一方当前所有合法走法（走法格式：静态棋类 fromto 如 b0c2 / e2e4；落子类单坐标如 j7 / e5）。",
    params: [
      { id: "gameId", name: "gameId", dataType: "string", required: true, description: "对局 id", value: "" },
      { id: "side", name: "side", dataType: "integer", required: false, description: "0=先手 1=后手，缺省当前行棋方", value: -1 },
    ],
  },
  {
    action: "make_move",
    name: "走一步棋",
    desc: "执行一个走法。走法字符串：fromto 或单坐标（国际象棋升变可加后缀 q/n/r/b，如 e7e8q；围棋可传 pass）。",
    params: [
      { id: "gameId", name: "gameId", dataType: "string", required: true, description: "对局 id", value: "" },
      { id: "move", name: "move", dataType: "string", required: true, description: "走法", value: "" },
    ],
  },
  {
    action: "undo",
    name: "悔棋",
    desc: "撤销上一步。返回当前局面。",
    params: [
      { id: "gameId", name: "gameId", dataType: "string", required: true, description: "对局 id", value: "" },
    ],
  },
];

const RULES_HINT: Record<string, string> = {
  go: "规则：黑白轮流在交叉点落子，气尽提子，禁自杀与打劫立即回提；连续两次虚着(pass)终局，黑贴 6.5 目。",
  gomoku: "规则：黑先白后，落于 15×15 交叉点，任意方向五连（含长连）即胜。",
  xiangqi: "规则：红先黑后，走法 fromto（如 b0c2）；将帅不可照面；被将军必须应将。",
  chess: "规则：白先黑后，走法 fromto（如 e2e4，升变加 q/n/r/b 如 e7e8q）；支持易位、吃过路兵。",
  jungle: "规则：蓝先红后，走法 fromto；象>狮>虎>豹>狼>狗>猫>鼠，鼠吃象；占领对方兽穴即胜。",
  junqi: "规则：黑先红后，走法 fromto；司令>军长>师长>旅长>团长>营长>连长>排长>工兵；工兵挖雷、炸弹同归于尽、军旗被吃即负。",
};

export interface ToolSyncReport {
  total: number;
  ok: number;
  failed: Array<{ id: string; reason: string }>;
}

export async function syncMcpTools(sdk: FatNotesPluginSDK): Promise<ToolSyncReport> {
  const report: ToolSyncReport = { total: 0, ok: 0, failed: [] };
  let bridgePort: number;
  try {
    const info = await sdk.backend.invoke<{ port: number }>("fatchess_bridge_info", {});
    bridgePort = info?.port;
  } catch (e) {
    report.failed.push({ id: "bridge", reason: `后端桥不可用: ${(e as Error).message}` });
    return report;
  }
  if (!bridgePort) {
    report.failed.push({ id: "bridge", reason: "后端桥未启动" });
    return report;
  }

  for (const game of GAMES) {
    const meta = GAME_MAP[game.id];
    const rule = RULES_HINT[game.id] || "";
    for (const act of ACTIONS) {
      const toolId = `${TOOL_PREFIX}_${game.id}_${act.action}`;
      report.total += 1;
      const payload = {
        id: toolId,
        name: `${meta.name}-${act.name}`,
        description: `${meta.name}：${act.desc}${rule ? "\n" + rule : ""}`,
        tags: ["fat-chess", meta.name],
        langs: ["zh"],
        type: "requestUrl",
        enable: true,
        conf: {
          url: `http://127.0.0.1:${bridgePort}/fatchess/${game.id}/${act.action}`,
          method: "post",
          inParams: act.params,
        },
      };
      try {
        const resp = await postHost(sdk, "/app/mcp/addTool", payload);
        if (!resp.isOk && /already|存在/i.test(resp.message || "")) {
          const edit = await postHost(sdk, "/app/mcp/editTool", payload);
          if (!edit.isOk) {
            report.failed.push({ id: toolId, reason: `editTool: ${edit.message}` });
            continue;
          }
        } else if (!resp.isOk) {
          report.failed.push({ id: toolId, reason: `addTool: ${resp.message}` });
          continue;
        }
        report.ok += 1;
      } catch (e) {
        report.failed.push({ id: toolId, reason: (e as Error).message });
      }
    }
  }
  return report;
}

interface HostResp {
  code: number;
  message: string;
  data: unknown;
  isOk: boolean;
}

async function postHost(
  sdk: FatNotesPluginSDK,
  path: string,
  body: unknown,
): Promise<HostResp> {
  const resp = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    throw new Error(`${path} HTTP ${resp.status}`);
  }
  const json = (await resp.json()) as HostResp;
  return json;
}
