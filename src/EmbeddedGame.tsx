/**
 * 嵌入式对局视图（仪表盘卡片用）。
 *
 * 与 PluginView 的 workbench 分支等价（未开局 → PreGameView，开局 → GameView），
 * 但有两点不同：
 *   1. 棋种由 `game` prop 强制决定，不读全局 store 的 ui.game；
 *   2. 对局会话 session 保存在组件本地 state，不写全局 chessStore，
 *      因此每张「棋游」卡片互相独立、也不干扰侧栏/工作区的那局。
 *
 * 模式 / AI 难度 / 路数 / 默认模型仍读全局 store——这些是用户级偏好，
 * 各处保持一致即可。父组件用 key={gameId} 切换棋种时本组件整体重挂载，
 * 本地 session 自然清空，回到该棋种的开局页。
 */
import React, { useMemo, useState } from "react";
import type { FatNotesPluginSDK } from "fat-notes-sdk";
import { makeApi } from "./api";
import GameView from "./GameView";
import PreGameView from "./PreGameView";
import { useChessState } from "./chessStore";
import type { SessionInfo } from "./types";

interface Props {
  sdk: FatNotesPluginSDK;
  game: string;
}

const EmbeddedGame: React.FC<Props> = ({ sdk, game }) => {
  const api = useMemo(() => makeApi(sdk), [sdk]);
  const ui = useChessState();
  const [session, setSession] = useState<SessionInfo | null>(null);

  if (!session || session.game !== game) {
    return (
      <PreGameView
        sdk={sdk}
        api={api}
        game={game}
        mode={ui.mode}
        aiLevel={ui.aiLevel}
        goSize={ui.goSize}
        modelId={ui.modelId}
        onStart={setSession}
      />
    );
  }

  return (
    <GameView
      sdk={sdk}
      api={api}
      session={session}
      modelId={ui.modelId}
      aiLevel={ui.aiLevel}
      onSessionChange={setSession}
    />
  );
};

export default EmbeddedGame;
