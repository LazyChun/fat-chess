/*
 * 「棋游」卡片（仪表盘块类型 fat-chess.game）
 *
 * 在一张仪表盘卡片内嵌渲染任选棋种，并通过顶栏/底栏的切换按钮
 * （按钮组或下拉框）在多个棋种间切换：
 *   - options.gameSwitcher.games         参与切换的棋种 id 列表
 *   - options.gameSwitcher.defaultGame   默认展示的棋种
 *   - options.gameSwitcher.showSwitch   是否展示切换按钮
 *   - options.gameSwitcher.switchStyle  切换控件样式：segmented | select
 *   - options.gameSwitcher.switchPosition 切换按钮位置：top | bottom
 *
 * config 由宿主注入（Block.Item.options），外框（标题/背景/圆角/边框/内边距）
 * 由宿主 BlockFrame 按 commonOptions 渲染，本组件只负责内容区。
 */
import React, { useEffect, useMemo, useState } from "react";
import { Empty, Segmented, Select } from "antd";
import type { FatNotesPluginSDK } from "fat-notes-sdk";
import { GAMES } from "./games";
import EmbeddedGame from "./EmbeddedGame";

/** 卡片私有配置（options.gameSwitcher） */
export interface GameSwitcherConf {
  /** 参与切换的棋种 id 列表；为空时回退为全部棋种 */
  games?: string[];
  /** 默认展示的棋种 id */
  defaultGame?: string;
  /** 是否展示切换按钮 */
  showSwitch?: boolean;
  /** 切换控件样式：segmented 按钮组（默认）| select 下拉框 */
  switchStyle?: "segmented" | "select";
  /** 切换按钮位置：top 顶部（默认）| bottom 底部 */
  switchPosition?: "top" | "bottom";
}

/** 从宿主注入的 config（Block.Item.options）中收窄私有配置 */
export function normalizeGameSwitcherConf(
  config: unknown,
): GameSwitcherConf {
  const conf = (
    config as { gameSwitcher?: GameSwitcherConf } | null | undefined
  )?.gameSwitcher;
  return conf && typeof conf === "object" ? conf : {};
}

interface Props {
  /** 宿主注入的 Block.Item.options */
  config?: unknown;
  /** 是否渲染在配置抽屉预览中 */
  inConfig?: boolean;
  sdk?: FatNotesPluginSDK;
}

const GameSwitcherBlock: React.FC<Props> = ({ config, sdk }) => {
  const conf = normalizeGameSwitcherConf(config);

  // 参与切换的棋种（过滤未知 id；配置为空时回退全部）
  const available = useMemo(() => {
    const ids =
      Array.isArray(conf.games) && conf.games.length
        ? conf.games
        : GAMES.map((g) => g.id);
    return ids
      .map((id) => GAMES.find((g) => g.id === id))
      .filter((g): g is NonNullable<typeof g> => !!g);
  }, [conf.games]);

  // 默认棋种：配置值失效时回退第一个
  const initialId = useMemo(() => {
    if (
      conf.defaultGame &&
      available.some((g) => g.id === conf.defaultGame)
    ) {
      return conf.defaultGame;
    }
    return available[0]?.id;
  }, [conf.defaultGame, available]);

  const [activeId, setActiveId] = useState<string | undefined>(initialId);

  // 配置面板改了棋种集/默认棋种后，让卡片回到默认棋种
  useEffect(() => {
    setActiveId(initialId);
  }, [initialId]);

  const active = available.find((g) => g.id === activeId) || available[0];

  const renderSwitchBar = (): React.ReactNode => {
    if (!available.length) return null;
    if (conf.switchStyle === "select") {
      return (
        <Select
          size="small"
          style={{ width: "100%" }}
          value={active?.id}
          onChange={(v) => setActiveId(v as string)}
          options={available.map((g) => ({
            value: g.id,
            label: `${g.emoji} ${g.name}`,
          }))}
        />
      );
    }
    return (
      <Segmented
        block
        size="small"
        value={active?.id}
        onChange={(v) => setActiveId(v as string)}
        options={available.map((g) => ({
          value: g.id,
          title: g.name,
          label: `${g.emoji} ${g.name}`,
        }))}
      />
    );
  };

  const showBar = conf.showSwitch !== false && available.length > 1;
  const barOnTop = conf.switchPosition !== "bottom";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
      }}
    >
      {showBar ? (
        <div style={{ flexShrink: 0, padding: "0 8px" }}>{renderSwitchBar()}</div>
      ) : null}
      <div style={{ flex: 1, minHeight: 0, overflow: "auto" }}>
        {active && sdk ? (
          <EmbeddedGame key={active.id} sdk={sdk} game={active.id} />
        ) : (
          <div
            style={{
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="尚未配置棋种"
            />
          </div>
        )}
      </div>
      {showBar && !barOnTop ? (
        <div style={{ flexShrink: 0, padding: "0 8px 8px" }}>{renderSwitchBar()}</div>
      ) : null}
    </div>
  );
};

export default GameSwitcherBlock;
