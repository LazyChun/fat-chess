/**
 * fat-chess 插件级共享 UI 状态。
 *
 * 宿主把「侧栏菜单」（PrimarySidebar）与「工作区对局」（WorkbenchPage）
 * 渲染为两个独立的 React 子树，各自持有一份 PluginView 实例。选中的
 * 棋种 / 对局模式 / 对局会话需要跨子树同步，因此放到模块级 store +
 * useSyncExternalStore，任何一侧的变更另一侧立即感知。
 */
import React from "react";
import type { GameMode, SessionInfo } from "./types";

export interface ChessUiState {
  /** 侧栏选中的棋种（Lobby 本地高亮，进入对局后由 session 决定） */
  game: string;
  mode: GameMode;
  aiLevel: number;
  goSize: number;
  modelId: string | null;
  /** 插件配置是否已加载完成 */
  cfgLoaded: boolean;
  /** 进行中的对局会话；null = 未开局，工作区显示空态 */
  session: SessionInfo | null;
}

let state: ChessUiState = {
  game: "xiangqi",
  mode: "ai",
  aiLevel: 2,
  goSize: 19,
  modelId: null,
  cfgLoaded: false,
  session: null,
};

const listeners = new Set<() => void>();

export function getChessState(): ChessUiState {
  return state;
}

export function setChessState(patch: Partial<ChessUiState>): void {
  state = { ...state, ...patch };
  listeners.forEach((l) => {
    try {
      l();
    } catch {
      /* ignore */
    }
  });
}

export function subscribeChess(cb: () => void): () => void {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

export function useChessState(): ChessUiState {
  return React.useSyncExternalStore(subscribeChess, getChessState);
}
