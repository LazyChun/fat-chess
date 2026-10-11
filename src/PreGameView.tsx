/**
 * 对战页面（未开局状态）：左侧选中棋种后，右侧工作区立即展示对应棋种的
 * 空棋盘与开局配置摘要，点击「开始对局」才真正创建会话进入对局。
 * 开局后由 PluginView 切换渲染 GameView。
 */
import React, { useCallback, useState } from "react";
import { Button, Space, Tag, Typography } from "antd";
import type { FatNotesPluginSDK } from "fat-notes-sdk";
import type { FatChessApi } from "./api";
import { errText } from "./api";
import { GameBoard } from "./boards";
import { GAME_MAP } from "./games";
import type { GameMode, GameState, SessionInfo } from "./types";

interface Props {
  sdk: FatNotesPluginSDK;
  api: FatChessApi;
  game: string;
  mode: GameMode;
  aiLevel: number;
  goSize: number;
  modelId: string | null;
  onStart: (s: SessionInfo) => void;
}

const MODE_NAMES: Record<GameMode, string> = {
  ai: "🤖 人机对战",
  llm: "🧠 对战大模型",
  pvp: "👥 本机双人",
};

const AI_LEVEL_NAMES: Record<number, string> = {
  1: "入门",
  2: "进阶",
  3: "大师",
};

const PreGameView: React.FC<Props> = ({
  sdk,
  api,
  game,
  mode,
  aiLevel,
  goSize,
  modelId,
  onStart,
}) => {
  const [starting, setStarting] = useState(false);
  const meta = GAME_MAP[game] || GAME_MAP.gomoku;

  // 空棋盘预览（未开局，禁止交互）
  const emptyState: GameState = {
    game,
    rows: meta.rows,
    cols: meta.cols,
    board: Array.from({ length: meta.rows }, () =>
      Array.from({ length: meta.cols }, () => "."),
    ),
    turn: 0,
    winner: null,
    endedReason: "",
    history: [],
  };

  const configText = (() => {
    const parts: string[] = [];
    if (mode === "ai") parts.push(`AI 难度：${AI_LEVEL_NAMES[aiLevel] || aiLevel}`);
    if (mode === "llm") parts.push(modelId ? `模型已选择` : "未选择模型");
    if (game === "go") parts.push(`棋盘：${goSize} 路`);
    return parts.join(" · ") || "默认规则";
  })();

  const doStart = useCallback(async () => {
    setStarting(true);
    try {
      const settings = game === "go" ? { size: goSize } : undefined;
      const s = await api.newGame({
        game,
        mode,
        aiLevel: mode === "ai" ? aiLevel : undefined,
        modelId: mode === "llm" ? modelId || undefined : undefined,
        settings,
      });
      onStart(s);
      sdk.ui.toast.success(`已开局：${meta.name}`);
    } catch (e) {
      sdk.ui.toast.error(`开局失败: ${errText(e)}`);
    } finally {
      setStarting(false);
    }
  }, [game, mode, aiLevel, goSize, modelId, api, onStart, sdk, meta.name]);

  return (
    <div style={{ padding: 12 }}>
      <Space style={{ marginBottom: 8 }} wrap>
        <Typography.Text strong style={{ fontSize: 16 }}>
          {meta.emoji} {meta.name}
        </Typography.Text>
        <Tag color={mode === "llm" ? "purple" : mode === "ai" ? "blue" : "green"}>
          {MODE_NAMES[mode]}
        </Tag>
      </Space>

      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", alignItems: "flex-start" }}>
        <div
          style={{
            background: "#faf7f2",
            borderRadius: 8,
            padding: 8,
            border: "1px solid #e8e2d8",
          }}
        >
          <GameBoard state={emptyState} interactive={false} />
        </div>

        <div style={{ minWidth: 220, maxWidth: 320, display: "flex", flexDirection: "column", gap: 10 }}>
          <div
            style={{
              padding: "10px 12px",
              borderRadius: 8,
              background: "#f6ffed",
              border: "1px solid #b7eb8f",
            }}
          >
            <Typography.Text strong>对局尚未开始</Typography.Text>
            <div style={{ marginTop: 4, fontSize: 12, color: "#666" }}>{meta.desc}</div>
          </div>

          <div style={{ fontSize: 12, color: "#888" }}>
            当前配置：{configText}
          </div>

          <Button
            type="primary"
            size="large"
            block
            loading={starting}
            onClick={() => void doStart()}
          >
            开始对局
          </Button>

          {meta.kind === "placement" && (
            <div style={{ fontSize: 12, color: "#aaa" }}>点击空白交叉点落子。</div>
          )}
          {meta.kind === "move" && (
            <div style={{ fontSize: 12, color: "#aaa" }}>先点己方棋子，再点目标格走子。</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PreGameView;
