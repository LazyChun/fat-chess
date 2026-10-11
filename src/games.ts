/**
 * 六种棋的元数据与棋子字形映射。
 * 棋盘坐标与后端一致：列 a..（左→右）+ 行 0..（上→下）。
 */
import type { GameMeta } from "./types";

export const GAMES: GameMeta[] = [
  {
    id: "go",
    name: "围棋",
    emoji: "⚫",
    tagline: "19 路围地之争，提子、打劫、数空",
    kind: "placement",
    rows: 19,
    cols: 19,
    desc: "9/13/19 路可选。黑贴 6.5 目，连续两次虚着终局，支持让子。",
  },
  {
    id: "gomoku",
    name: "五子棋",
    emoji: "✦",
    tagline: "15×15 连五即胜",
    kind: "placement",
    rows: 15,
    cols: 15,
    desc: "黑先白后，横竖斜任意方向五连（含长连）即胜。",
  },
  {
    id: "xiangqi",
    name: "中国象棋",
    emoji: "♟",
    tagline: "九宫飞将，马蹩腿，炮隔山打",
    kind: "move",
    rows: 10,
    cols: 9,
    desc: "红先黑后。完整实现：蹩马腿、塞象眼、炮架、过河兵、飞将、应将与将死/困毙。",
  },
  {
    id: "chess",
    name: "国际象棋",
    emoji: "♞",
    tagline: "易位、吃过路兵、升变、逼和",
    kind: "move",
    rows: 8,
    cols: 8,
    desc: "白先黑后。支持易位、吃过路兵、兵升变（q/n/r/b）、将死、逼和、50 回合与三次重复。",
  },
  {
    id: "jungle",
    name: "斗兽棋",
    emoji: "🐅",
    tagline: "象狮虎豹狼狗猫鼠，鼠吃象",
    kind: "move",
    rows: 7,
    cols: 9,
    desc: "蓝方先手。兽穴制胜、行营免疫、陷阱吃子、鼠游河、狮虎跳河。",
  },
  {
    id: "junqi",
    name: "军棋（明盘）",
    emoji: "🎖",
    tagline: "军衔吃子，工兵挖雷，炸弹同归于尽",
    kind: "move",
    rows: 10,
    cols: 9,
    desc: "明盘变体。铁路直行、工兵可越子拐弯、大本营禁移、军旗被吃即负。",
  },
];

export const GAME_MAP: Record<string, GameMeta> = Object.fromEntries(
  GAMES.map((g) => [g.id, g]),
);

// ── 棋子字形 ────────────────────────────────────────────────

export const XQ_PIECE_NAMES: Record<string, string> = {
  K: "帅",
  A: "仕",
  B: "相",
  N: "马",
  R: "车",
  C: "炮",
  P: "兵",
  k: "将",
  a: "士",
  b: "象",
  n: "马",
  r: "车",
  c: "炮",
  p: "卒",
};

export const CHESS_GLYPHS: Record<string, string> = {
  K: "♔",
  Q: "♕",
  R: "♖",
  B: "♗",
  N: "♘",
  P: "♙",
  k: "♚",
  q: "♛",
  r: "♜",
  b: "♝",
  n: "♞",
  p: "♟",
};

export const JUNGLE_NAMES: Record<string, string> = {
  E: "象",
  L: "狮",
  T: "虎",
  P: "豹",
  W: "狼",
  D: "狗",
  C: "猫",
  R: "鼠",
  e: "象",
  l: "狮",
  t: "虎",
  p: "豹",
  w: "狼",
  d: "狗",
  c: "猫",
  r: "鼠",
};

export const JUNQI_NAMES: Record<string, string> = {
  S: "司令",
  J: "军长",
  Z: "师长",
  L: "旅长",
  T: "团长",
  Y: "营长",
  C: "连长",
  P: "排长",
  G: "工兵",
  M: "地雷",
  B: "炸弹",
  F: "军旗",
  s: "司令",
  j: "军长",
  z: "师长",
  l: "旅长",
  t: "团长",
  y: "营长",
  c: "连长",
  p: "排长",
  g: "工兵",
  m: "地雷",
  b: "炸弹",
  f: "军旗",
};

/** 军棋行营（双方阵营中心三点），用于棋盘渲染标记 */
export const JUNQI_CAMPS = [
  [
    [2, 3],
    [2, 4],
    [2, 5],
    [1, 4],
  ],
  [
    [7, 3],
    [7, 4],
    [7, 5],
    [8, 4],
  ],
];

/** 军棋大本营 */
export const JUNQI_FORTS = [
  [
    [0, 2],
    [0, 6],
  ],
  [
    [9, 2],
    [9, 6],
  ],
];

/** 斗兽棋兽穴（蓝方行0，红方行6），列 4 */
export const JUNGLE_DENS = [
  [0, 4],
  [6, 4],
];

/** 斗兽棋陷阱 */
export const JUNGLE_TRAPS = [
  [
    [0, 3],
    [0, 5],
    [2, 4],
  ],
  [
    [6, 3],
    [6, 5],
    [4, 4],
  ],
];

/** 斗兽棋河流格子（行 3，列 1..7） */
export const JUNGLE_RIVER = Array.from({ length: 7 }, (_, c) => [3, c + 1]);

export function colLetter(col: number): string {
  return String.fromCharCode(97 + col);
}

export function sqText(row: number, col: number): string {
  return colLetter(col) + String(row);
}

/** 判断某个棋格是否为空白 */
export function isEmptyCell(v: string | number | undefined | null): boolean {
  return v === undefined || v === null || v === "" || v === "." || v === -1;
}
