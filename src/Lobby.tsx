/**
 * 游戏菜单（宿主主侧栏窄版）：选择棋种、对局模式（人机/对战大模型/双人）、
 * AI 难度与模型。所有选择通过 syncConfig 写入本地 store 并广播到宿主事件
 * 总线，右侧工作区实时渲染对应棋种的对战页面；开局按钮在右侧对战页面内。
 */
import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Divider,
  Radio,
  Select,
  Space,
  Tag,
  Typography,
} from "antd";
import type { FatNotesPluginSDK } from "fat-notes-sdk";
import type { FatChessApi } from "./api";
import { errText } from "./api";
import { GAMES } from "./games";
import { syncMcpTools, type ToolSyncReport } from "./mcp";
import type { AiModelOption, GameMode } from "./types";
import { useChessState } from "./chessStore";
import { syncConfig } from "./PluginView";

interface Props {
  sdk: FatNotesPluginSDK;
  api: FatChessApi;
  modelId: string | null;
  aiLevel: number;
}

const Lobby: React.FC<Props> = ({ sdk, api, modelId, aiLevel }) => {
  const ui = useChessState();
  const [models, setModels] = useState<AiModelOption[]>([]);
  const [modelsLoaded, setModelsLoaded] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncReport, setSyncReport] = useState<ToolSyncReport | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const list = await sdk.ai.getModels();
        setModels((list || []) as AiModelOption[]);
        setModelsLoaded(true);
        if (!modelId && list?.length) {
          const def = list.find((m) => (m as AiModelOption).isDefault) || list[0];
          syncConfig(sdk, { modelId: (def as AiModelOption).id });
        }
      } catch {
        setModelsLoaded(true);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const doSyncTools = useCallback(async () => {
    setSyncing(true);
    setSyncReport(null);
    try {
      const r = await syncMcpTools(sdk);
      setSyncReport(r);
      if (r.failed.length === 0) sdk.ui.toast.success(`已同步 ${r.ok} 个下棋工具`);
      else sdk.ui.toast.warn(`同步完成：成功 ${r.ok}，失败 ${r.failed.length}`);
    } catch (e) {
      sdk.ui.toast.error(`同步失败: ${errText(e)}`);
    } finally {
      setSyncing(false);
    }
  }, [sdk]);

  /** 选中棋种：切换棋种即退出当前对局，回到该棋种的对战页面（广播同步） */
  const selectGame = (id: string) => {
    syncConfig(sdk, { game: id, session: null });
  };

  const selectMode = (m: GameMode) => {
    syncConfig(sdk, { mode: m });
  };

  return (
    <div style={{ padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <Typography.Title level={5} style={{ margin: 0 }}>
          ♟ fat-chess
        </Typography.Title>
        <Button size="small" loading={syncing} onClick={() => void doSyncTools()}>
          同步工具
        </Button>
      </div>
      {syncReport && (
        <div
          style={{
            marginTop: 6,
            fontSize: 11,
            color: syncReport.failed.length ? "#fa8c16" : "#52c41a",
          }}
        >
          工具同步：{syncReport.ok}/{syncReport.total}
          {syncReport.failed.length > 0 &&
            `；失败 ${syncReport.failed.length}`}
        </div>
      )}

      <Divider style={{ margin: "10px 0" }} />

      {/* 模式 */}
      <div style={{ marginBottom: 12 }}>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          模式
        </Typography.Text>
        <Radio.Group
          value={ui.mode}
          onChange={(e) => selectMode(e.target.value as GameMode)}
          style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 6 }}
        >
          <Radio value="ai">🤖 人机对战</Radio>
          <Radio value="llm">🧠 对战大模型</Radio>
          <Radio value="pvp">👥 本机双人</Radio>
        </Radio.Group>
      </div>

      {ui.mode === "ai" && (
        <div style={{ marginBottom: 12 }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            AI 难度
          </Typography.Text>
          <Select
            value={aiLevel}
            onChange={(lvl) => syncConfig(sdk, { aiLevel: lvl })}
            style={{ width: "100%", marginTop: 4 }}
            options={[
              { label: "入门", value: 1 },
              { label: "进阶", value: 2 },
              { label: "大师", value: 3 },
            ]}
          />
        </div>
      )}
      {ui.mode === "llm" && (
        <div style={{ marginBottom: 12 }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            大模型
          </Typography.Text>
          <Select
            style={{ width: "100%", marginTop: 4 }}
            value={modelId || undefined}
            placeholder={modelsLoaded ? "请选择模型" : "加载模型中…"}
            onChange={(id) => syncConfig(sdk, { modelId: id })}
            options={models.map((m) => ({
              label: `${m.name}${m.isDefault ? "（默认）" : ""}`,
              value: m.id,
            }))}
          />
          <div style={{ marginTop: 4, fontSize: 11, color: "#999" }}>
            模型通过宿主 MCP 下棋工具自动落子。
          </div>
        </div>
      )}
      {ui.game === "go" && (
        <div style={{ marginBottom: 12 }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            棋盘路数
          </Typography.Text>
          <Radio.Group
            value={ui.goSize}
            onChange={(e) => syncConfig(sdk, { goSize: e.target.value as number })}
            style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 6 }}
          >
            <Radio value={9}>9 路</Radio>
            <Radio value={13}>13 路</Radio>
            <Radio value={19}>19 路</Radio>
          </Radio.Group>
        </div>
      )}

      <Divider style={{ margin: "10px 0" }} />

      {/* 棋种列表 */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {GAMES.map((g) => {
          const active = ui.game === g.id;
          return (
            <div
              key={g.id}
              onClick={() => selectGame(g.id)}
              style={{
                border: "1px solid " + (active ? "#1677ff" : "#e8e8e8"),
                borderRadius: 6,
                padding: "6px 8px",
                cursor: "pointer",
                background: active ? "#e6f4ff" : "#fff",
                transition: "all .15s",
              }}
            >
              <Space size={6}>
                <span style={{ fontSize: 15 }}>{g.emoji}</span>
                <span style={{ fontWeight: active ? 600 : 400, fontSize: 13 }}>
                  {g.name}
                </span>
                {active && <Tag color="blue" style={{ marginInlineEnd: 0, fontSize: 10 }}>已选</Tag>}
              </Space>
              <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>{g.tagline}</div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 10, fontSize: 11, color: "#999" }}>
        右侧对战页面中选择开局。
      </div>
    </div>
  );
};

export default Lobby;
