/**
 * fat-chess 前端公共类型
 * 与后端 engines/service.py、engines/base.py 返回结构对齐。
 */

export type GameMode = "ai" | "llm" | "pvp";

export interface GameMeta {
  id: string;
  name: string;
  emoji: string;
  tagline: string;
  kind: "placement" | "move"; // placement=落子类(go/gomoku)，move=走子类
  rows: number;
  cols: number;
  desc: string;
}

/** 后端 new_game / get_state / make_move 返回的 state */
export interface GameState {
  game: string;
  rows: number;
  cols: number;
  size?: number;
  board: Array<Array<string | number>>;
  turn: number;
  winner: number | null; // null=进行中, 0/1=某方胜, -1=和
  endedReason: string;
  lastMove?: string;
  inCheck?: boolean[];
  history?: string[];
  captured?: number[];
  text?: string;
  [k: string]: unknown;
}

/** new_game / llm_move 等返回的会话对象 */
export interface SessionInfo {
  gameId: string;
  game: string;
  mode: GameMode;
  state: GameState;
  aiSide?: number;
  aiLevel?: number;
  modelId?: string | null;
}

export interface RpcResult<T = unknown> {
  ok: boolean;
  error?: string;
  data?: T;
}

export interface AiModelOption {
  id: string;
  name: string;
  model?: string;
  url?: string;
  isDefault?: boolean;
}
