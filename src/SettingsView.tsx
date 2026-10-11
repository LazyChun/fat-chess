/**
 * 插件设置页：默认大模型、下棋工具同步、后端桥状态。
 */
import React, { useCallback, useEffect, useState } from "react";
import { Alert, Button, Card, Descriptions, Select, Space, Typography } from "antd";
import type { FatNotesPluginSDK } from "fat-notes-sdk";
import type { FatChessApi } from "./api";
import { errText } from "./api";
import { syncMcpTools, type ToolSyncReport } from "./mcp";
import type { AiModelOption } from "./types";

interface Props {
  sdk: FatNotesPluginSDK;
  api: FatChessApi;
  modelId: string | null;
  onModelIdChange: (id: string | null) => void;
}

const SettingsView: React.FC<Props> = ({ sdk, api, modelId, onModelIdChange }) => {
  const [models, setModels] = useState<AiModelOption[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [bridge, setBridge] = useState<{ port: number; baseUrl: string } | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [report, setReport] = useState<ToolSyncReport | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const list = await sdk.ai.getModels();
        setModels((list || []) as AiModelOption[]);
      } catch {
        /* 宿主未配置模型 */
      } finally {
        setLoaded(true);
      }
      try {
        const info = await api.bridgeInfo();
        setBridge(info);
      } catch {
        /* 桥未就绪 */
      }
    })();
  }, [sdk, api]);

  const doSync = useCallback(async () => {
    setSyncing(true);
    try {
      const r = await syncMcpTools(sdk);
      setReport(r);
      if (!r.failed.length) sdk.ui.toast.success(`已同步 ${r.ok} 个下棋工具`);
      else sdk.ui.toast.warn(`成功 ${r.ok}，失败 ${r.failed.length}`);
    } catch (e) {
      sdk.ui.toast.error(`同步失败: ${errText(e)}`);
    } finally {
      setSyncing(false);
    }
  }, [sdk]);

  return (
    <div style={{ padding: 16, maxWidth: 680 }}>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        fat-chess 设置
      </Typography.Title>

      <Card size="small" title="默认大模型（对战大模型模式使用）" style={{ marginBottom: 16 }}>
        {!loaded ? (
          <Typography.Text type="secondary">加载模型中…</Typography.Text>
        ) : models.length === 0 ? (
          <Alert
            type="warning"
            showIcon
            message="宿主尚未配置 AI 模型"
            description="请到宿主的 AI 设置中添加模型后刷新本页。大模型对战依赖宿主模型配置。"
          />
        ) : (
          <Select
            style={{ width: "100%" }}
            value={modelId || undefined}
            placeholder="选择默认模型"
            onChange={onModelIdChange}
            options={models.map((m) => ({
              label: `${m.name}${m.isDefault ? "（默认）" : ""}${m.model ? ` · ${m.model}` : ""}`,
              value: m.id,
            }))}
          />
        )}
      </Card>

      <Card
        size="small"
        title="下棋 MCP 工具"
        extra={
          <Button size="small" loading={syncing} onClick={() => void doSync()}>
            立即同步
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
          把 6 种棋 × 5 个动作（开新局/看局面/列走法/走棋/悔棋）注册为宿主的
          requestUrl 工具，指向插件后端内置的本地 HTTP 桥。大模型可通过这些工具直接落子。
        </Typography.Paragraph>
        {report && (
          <div style={{ fontSize: 12, color: report.failed.length ? "#fa8c16" : "#52c41a" }}>
            成功 {report.ok}/{report.total}
            {report.failed.length > 0 && `；失败：${report.failed.map((f) => f.id).join("、")}`}
          </div>
        )}
      </Card>

      <Card size="small" title="后端桥状态">
        <Descriptions size="small" column={1}>
          <Descriptions.Item label="状态">{bridge ? "运行中" : "未启动"}</Descriptions.Item>
          <Descriptions.Item label="地址">{bridge ? bridge.baseUrl : "-"}</Descriptions.Item>
          <Descriptions.Item label="端口">{bridge ? bridge.port : "-"}</Descriptions.Item>
        </Descriptions>
        <Space style={{ marginTop: 8 }}>
          <Button
            size="small"
            onClick={() => {
              void (async () => {
                try {
                  const info = await api.bridgeInfo();
                  setBridge(info);
                  sdk.ui.toast.success("桥已刷新");
                } catch (e) {
                  sdk.ui.toast.error(errText(e));
                }
              })();
            }}
          >
            刷新状态
          </Button>
        </Space>
      </Card>
    </div>
  );
};

export default SettingsView;
