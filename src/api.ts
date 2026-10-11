/**
 * 后端 JSON-RPC 访问封装。
 * 所有棋局操作统一走 sdk.backend.invoke("fatchess_rpc", {action, ...})。
 */
import type { FatNotesPluginSDK } from "fat-notes-sdk";
import type { GameState, SessionInfo } from "./types";

export function makeApi(sdk: FatNotesPluginSDK) {
  const rpc = <T = unknown>(
    action: string,
    params: Record<string, unknown> = {},
    timeout?: number,
  ): Promise<T> =>
    sdk.backend.invoke<T>("fatchess_rpc", { action, ...params }, timeout);

  return {
    rpc,

    async newGame(opts: {
      game: string;
      mode: string;
      aiLevel?: number;
      modelId?: string;
      settings?: Record<string, unknown>;
    }): Promise<SessionInfo> {
      return rpc<SessionInfo>("new_game", opts);
    },

    async getState(gameId: string): Promise<GameState> {
      // 后端返回 {gameId, game, state}，解包出真正的 GameState
      const r = await rpc<{ gameId: string; game?: string; state: GameState }>(
        "get_state",
        { gameId },
      );
      return r.state ?? (r as unknown as GameState);
    },

    async makeMove(gameId: string, move: string): Promise<GameState> {
      const r = await rpc<{ gameId: string; state: GameState; move?: string }>(
        "make_move",
        { gameId, move },
      );
      return r.state ?? (r as unknown as GameState);
    },

    async undo(gameId: string): Promise<GameState> {
      const r = await rpc<{ gameId: string; state: GameState }>("undo", {
        gameId,
      });
      return r.state ?? (r as unknown as GameState);
    },

    async resign(gameId: string): Promise<GameState> {
      const r = await rpc<{ gameId: string; state: GameState }>("resign", {
        gameId,
      });
      return r.state ?? (r as unknown as GameState);
    },

    async aiMove(gameId: string, level?: number): Promise<{ move: string; state: GameState }> {
      const params: Record<string, unknown> = { gameId };
      if (level != null) params.level = level;
      return rpc("ai_move", params, 120);
    },

    async legalMoves(gameId: string, side?: number): Promise<{ moves: string[]; side: number }> {
      return rpc("legal_moves", { gameId, side });
    },

    /** 大模型走子（后端经 host_call ai.chat + MCP 工具完成） */
    async llmMove(
      gameId: string,
      modelId?: string,
      extraPrompt?: string,
    ): Promise<{
      state: GameState;
      content: string;
      moved: boolean;
      model?: string;
    }> {
      return sdk.backend.invoke(
        "fatchess_llm_move",
        { gameId, modelId, extraPrompt },
        600,
      );
    },

    async bridgeInfo(): Promise<{ port: number; baseUrl: string; started: boolean }> {
      return sdk.backend.invoke("fatchess_bridge_info", {});
    },
  };
}

export type FatChessApi = ReturnType<typeof makeApi>;

/** 把后端抛出的错误转成可读文本 */
export function errText(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}
