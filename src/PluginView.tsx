/**
 * fat-chess 视图分发：
 * - view="menu"      宿主主侧栏（PrimarySidebar）——棋种菜单
 * - view="workbench" 宿主工作区（WorkbenchPage）——对局界面
 * - view="settings"  设置页
 *
 * 侧栏与工作区是宿主两个独立的 React 子树。为了不依赖「模块级 store 在
 * 多个渲染子树间同步」的假设，所有跨子树配置（棋种/模式/路数/难度/模型）
 * 统一走宿主 sdk.events 事件总线广播（sdk 是宿主创建的单例，对所有子树
 * 可靠），每个子树再写入本地 store。开局会话 session 只由工作区持有。
 */
import React, { useEffect, useMemo } from "react";
import type { FatNotesPluginSDK } from "fat-notes-sdk";
import { makeApi } from "./api";
import GameView from "./GameView";
import Lobby from "./Lobby";
import PreGameView from "./PreGameView";
import SettingsView from "./SettingsView";
import {
  getChessState,
  setChessState,
  useChessState,
} from "./chessStore";
import type { ChessUiState } from "./chessStore";

interface Props {
  sdk: FatNotesPluginSDK;
  view?: string; // "menu" | "workbench" | "settings"
}

/** 事件名：侧栏配置变更广播 */
const LOBBY_EVENT = "fat-chess:lobby";

/**
 * 更新本地 store 并广播完整配置快照到宿主事件总线。
 * 所有视图（menu/workbench/settings）监听该事件并同步自己的 store，
 * 从而保证左侧选中什么，右侧就显示什么。
 */
export function syncConfig(
  sdk: FatNotesPluginSDK,
  patch: Partial<ChessUiState>,
): void {
  const next = { ...getChessState(), ...patch };
  setChessState(patch);
  sdk.events.emit(LOBBY_EVENT, {
    game: next.game,
    mode: next.mode,
    goSize: next.goSize,
    aiLevel: next.aiLevel,
    modelId: next.modelId,
  });
}

const PluginView: React.FC<Props> = ({ sdk, view = "menu" }) => {
  const api = useMemo(() => makeApi(sdk), [sdk]);
  const ui = useChessState();

  // 加载插件配置（默认模型 / AI 难度）。所有实例都会执行，幂等。
  useEffect(() => {
    void (async () => {
      try {
        const cfg = await sdk.config.get<{ modelId?: string; aiLevel?: number }>();
        setChessState({
          modelId: cfg?.modelId ?? null,
          aiLevel: typeof cfg?.aiLevel === "number" ? cfg.aiLevel : 2,
          cfgLoaded: true,
        });
      } catch {
        setChessState({ cfgLoaded: true });
      }
    })();
  }, [sdk]);

  // 订阅侧栏广播的配置快照，保持本实例 store 与全局一致。
  useEffect(() => {
    const d = sdk.events.on(LOBBY_EVENT, (payload) => {
      const p = (payload || {}) as Partial<ChessUiState>;
      const patch: Partial<ChessUiState> = {};
      if (typeof p.game === "string") {
        patch.game = p.game;
        // 切换棋种即退出当前对局，回到该棋种的对战页面
        patch.session = null;
      }
      if (typeof p.mode === "string") patch.mode = p.mode;
      if (typeof p.goSize === "number") patch.goSize = p.goSize;
      if (typeof p.aiLevel === "number") patch.aiLevel = p.aiLevel;
      if (typeof p.modelId === "string" || p.modelId === null) {
        patch.modelId = p.modelId;
      }
      if (Object.keys(patch).length > 0) setChessState(patch);
    });
    return () => d.dispose();
  }, [sdk]);

  if (view === "settings") {
    return (
      <SettingsView
        sdk={sdk}
        api={api}
        modelId={ui.modelId}
        onModelIdChange={(id) => syncConfig(sdk, { modelId: id })}
      />
    );
  }

  if (view === "workbench") {
    if (!ui.cfgLoaded) {
      return <div style={{ padding: 24, color: "#999" }}>加载中…</div>;
    }
    // 没有对局，或对局棋种与当前选中不一致时，都显示选中棋种的对战页面，
    // 避免「左侧选中象棋、右侧却挂着五子棋对局」这类状态错乱。
    if (!ui.session || ui.session.game !== ui.game) {
      return (
        <PreGameView
          sdk={sdk}
          api={api}
          game={ui.game}
          mode={ui.mode}
          aiLevel={ui.aiLevel}
          goSize={ui.goSize}
          modelId={ui.modelId}
          onStart={(s) => setChessState({ game: s.game, session: s })}
        />
      );
    }
    return (
      <GameView
        sdk={sdk}
        api={api}
        session={ui.session}
        modelId={ui.modelId}
        aiLevel={ui.aiLevel}
        onSessionChange={(s) => setChessState({ game: s.game, session: s })}
      />
    );
  }

  // 默认：侧栏菜单
  if (!ui.cfgLoaded) {
    return <div style={{ padding: 24, color: "#999" }}>加载中…</div>;
  }
  return (
    <Lobby
      sdk={sdk}
      api={api}
      modelId={ui.modelId}
      aiLevel={ui.aiLevel}
    />
  );
};

export default PluginView;
