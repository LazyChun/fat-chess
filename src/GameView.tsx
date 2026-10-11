/**
 * 单局对战视图：棋盘 + 走子交互 + 人机/大模型/双人控制。
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Button, Space, Tag, Typography } from "antd";
import type { FatNotesPluginSDK } from "fat-notes-sdk";
import type { FatChessApi } from "./api";
import { errText } from "./api";
import { GameBoard } from "./boards";
import { GAME_MAP } from "./games";
import type { GameState, GameMode, SessionInfo } from "./types";

interface Props {
  sdk: FatNotesPluginSDK;
  api: FatChessApi;
  session: SessionInfo;
  modelId?: string | null;
  aiLevel: number;
  onSessionChange: (s: SessionInfo) => void;
}

const SIDE_NAMES: Record<string, [string, string]> = {
  go: ["黑方", "白方"],
  gomoku: ["黑方", "白方"],
  xiangqi: ["红方", "黑方"],
  chess: ["白方", "黑方"],
  jungle: ["蓝方", "红方"],
  junqi: ["黑方", "红方"],
};

const END_REASONS: Record<string, string> = {
  checkmate: "将死",
  stalemate: "困毙/逼和",
  five: "五连",
  draw: "满盘",
  resign: "认输",
  den: "占领兽穴",
  flag: "军旗被吃",
  no_pieces: "无子可走",
  move_limit: "步数上限",
  fifty: "50 回合",
  repetition: "三次重复",
  score: "数子",
};

const GameView: React.FC<Props> = ({
  sdk,
  api,
  session,
  modelId,
  aiLevel,
  onSessionChange,
}) => {
  const [state, setState] = useState<GameState>(session.state);
  const [legalMoves, setLegalMoves] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [llmNote, setLlmNote] = useState("");

  const meta = GAME_MAP[state.game] || GAME_MAP.gomoku;
  const sideNames = SIDE_NAMES[state.game] || ["先手", "后手"];

  const humanSide = session.mode === "pvp" ? null : 0;
  const llmTurn =
    session.mode === "llm" && state.turn === 1 && state.winner === null;

  const refreshMoves = useCallback(
    async (st: GameState) => {
      try {
        const r = await api.legalMoves(session.gameId, st.turn);
        setLegalMoves(r.moves || []);
      } catch {
        setLegalMoves([]);
      }
    },
    [api, session.gameId],
  );

  const applyState = useCallback(
    async (st: GameState) => {
      setState(st);
      setSelected(null);
      void refreshMoves(st);
      onSessionChange({ ...session, state: st });
    },
    [refreshMoves, session, onSessionChange],
  );

  // 首次挂载 / 会话变化时同步状态
  useEffect(() => {
    void (async () => {
      try {
        const st = await api.getState(session.gameId);
        await applyState(st);
      } catch (e) {
        sdk.ui.toast.error(`读取局面失败: ${errText(e)}`);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.gameId]);

  const humanMove = useCallback(
    async (move: string) => {
      if (busy || state.winner !== null) return;
      if (session.mode !== "pvp" && state.turn !== 0) return;
      setBusy(true);
      try {
        const st = await api.makeMove(session.gameId, move);
        await applyState(st);
        // 人机：轮到 AI 自动走
        if (session.mode === "ai" && st.winner === null) {
          const r = await api.aiMove(session.gameId, aiLevel);
          await applyState(r.state);
          sdk.ui.toast.info(`AI 走了 ${r.move}`);
        }
      } catch (e) {
        sdk.ui.toast.error(errText(e));
      } finally {
        setBusy(false);
      }
    },
    [busy, state.winner, state.turn, session, api, aiLevel, applyState, sdk],
  );

  const llmMove = useCallback(async () => {
    if (busy || state.winner !== null) return;
    setBusy(true);
    setLlmNote("大模型思考中，可能需要十几秒…");
    try {
      const r = await api.llmMove(session.gameId, modelId || undefined);
      await applyState(r.state);
      if (r.moved) {
        setLlmNote(r.content ? `大模型：${r.content.slice(0, 200)}` : "大模型已落子");
      } else {
        setLlmNote(`大模型未落子：${r.content ? r.content.slice(0, 200) : "无输出"}`);
      }
    } catch (e) {
      setLlmNote("");
      sdk.ui.toast.error(`大模型走棋失败: ${errText(e)}`);
    } finally {
      setBusy(false);
    }
  }, [busy, state.winner, session.gameId, modelId, api, applyState, sdk]);

  const doUndo = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    try {
      let st = await api.undo(session.gameId);
      // 人机/大模型模式：AI 刚走完时，悔棋应连退两步回到人类走子前
      if (
        session.mode !== "pvp" &&
        st.winner === null &&
        st.turn === 1 &&
        st.history &&
        st.history.length > 0
      ) {
        st = await api.undo(session.gameId);
      }
      await applyState(st);
    } catch (e) {
      sdk.ui.toast.error(errText(e));
    } finally {
      setBusy(false);
    }
  }, [busy, session, api, applyState, sdk]);

  const doResign = useCallback(async () => {
    if (busy || state.winner !== null) return;
    const ok = await sdk.ui.modal.confirm({
      title: "认输",
      content: "确定要认输吗？",
      okText: "认输",
      cancelText: "取消",
    });
    if (!ok) return;
    setBusy(true);
    try {
      const st = await api.resign(session.gameId);
      await applyState(st);
    } catch (e) {
      sdk.ui.toast.error(errText(e));
    } finally {
      setBusy(false);
    }
  }, [busy, state.winner, api, session.gameId, applyState, sdk]);

  const doRestart = useCallback(async () => {
    if (busy) return;
    setBusy(true);
    try {
      const s = await api.newGame({
        game: state.game,
        mode: session.mode,
        aiLevel: session.mode === "ai" ? aiLevel : undefined,
        modelId: session.mode === "llm" ? modelId || undefined : undefined,
      });
      onSessionChange(s);
      setState(s.state);
      setSelected(null);
      setLlmNote("");
      await refreshMoves(s.state);
    } catch (e) {
      sdk.ui.toast.error(errText(e));
    } finally {
      setBusy(false);
    }
  }, [busy, state.game, session.mode, aiLevel, modelId, api, onSessionChange, refreshMoves, sdk]);

  const interactive =
    !busy && state.winner === null &&
    (session.mode === "pvp" || state.turn === humanSide);

  const statusText = useMemo(() => {
    if (state.winner !== null) {
      if (state.winner === -1) return "和棋";
      const w = state.winner === 0 ? sideNames[0] : sideNames[1];
      const reason = END_REASONS[state.endedReason] || state.endedReason;
      return `${w}胜（${reason}）`;
    }
    const t = state.turn === 0 ? sideNames[0] : sideNames[1];
    let modeText = "";
    if (session.mode === "ai") modeText = ` ｜ 人机`;
    else if (session.mode === "llm") modeText = ` ｜ 对战大模型`;
    else modeText = ` ｜ 双人`;
    return `轮到 ${t}${modeText}`;
  }, [state.winner, state.turn, state.endedReason, sideNames, session.mode]);

  const modeTag = session.mode === "ai" ? "人机" : session.mode === "llm" ? "对战大模型" : "双人";

  return (
    <div style={{ padding: 12 }}>
      <Space style={{ marginBottom: 8 }} wrap>
        <Typography.Text strong style={{ fontSize: 16 }}>
          {meta.emoji} {meta.name}
        </Typography.Text>
        <Tag color={session.mode === "llm" ? "purple" : session.mode === "ai" ? "blue" : "green"}>
          {modeTag}
        </Tag>
        {state.inCheck && state.inCheck[state.turn] ? <Tag color="red">将军！</Tag> : null}
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
          <GameBoard
            state={state}
            legalMoves={legalMoves}
            selected={selected}
            interactive={interactive}
            onPlacementMove={(sq) => void humanMove(sq)}
            onMove={(from, to) => void humanMove(from + to)}
            onSelect={setSelected}
          />
        </div>

        <div style={{ minWidth: 220, maxWidth: 320, display: "flex", flexDirection: "column", gap: 10 }}>
          <div
            style={{
              padding: "10px 12px",
              borderRadius: 8,
              background: state.winner !== null ? "#fff7e6" : "#f6ffed",
              border: "1px solid " + (state.winner !== null ? "#ffd591" : "#b7eb8f"),
            }}
          >
            <Typography.Text strong>{statusText}</Typography.Text>
            {state.winner === null && session.mode === "llm" && (
              <div style={{ marginTop: 4, fontSize: 12, color: "#666" }}>
                {llmTurn ? "轮到大模型走棋" : "轮到人类走棋"}
              </div>
            )}
            {llmNote && <div style={{ marginTop: 6, fontSize: 12, color: "#722ed1" }}>{llmNote}</div>}
          </div>

          {session.mode === "llm" && llmTurn && (
            <Button type="primary" block loading={busy} onClick={() => void llmMove()} icon={<span>🤖</span>}>
              让大模型走一步
            </Button>
          )}

          <Space wrap>
            <Button size="small" onClick={() => void doUndo()} disabled={busy || state.history?.length === 0}>
              悔棋
            </Button>
            <Button size="small" danger onClick={() => void doResign()} disabled={busy || state.winner !== null}>
              认输
            </Button>
            <Button size="small" onClick={() => void doRestart()} disabled={busy}>
              重开
            </Button>
          </Space>

          {meta.kind === "move" && (
            <div style={{ fontSize: 12, color: "#888" }}>
              先点己方棋子，再点目标格走子。
            </div>
          )}
          {meta.kind === "placement" && (
            <div style={{ fontSize: 12, color: "#888" }}>点击空白交叉点落子。</div>
          )}
          {session.mode === "llm" && (
            <div style={{ fontSize: 12, color: "#888" }}>
              大模型通过宿主 MCP 下棋工具直接落子；每次走棋约需十几秒到一分钟。
            </div>
          )}
          <div style={{ fontSize: 12, color: "#aaa" }}>
            {state.history?.length ?? 0} 手棋
          </div>
        </div>
      </div>
    </div>
  );
};

export default GameView;
