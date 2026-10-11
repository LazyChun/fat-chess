/*
 * fat-chess 插件入口。
 *
 * - activate：注册侧栏视图、设置页与命令，并（尽力）同步下棋 MCP 工具。
 * - deactivate：释放全部注册。
 *
 * 注意：secondary 侧栏为宿主聊天保留，任何注册都会被宿主拒绝。
 */
import React from "react";
import type { Disposable, FatNotesPluginSDK } from "fat-notes-sdk";
import PluginView from "./PluginView";
import { syncMcpTools } from "./mcp";
import { CHESS_GAME_ICON_URL } from "./assets/chessIcon";
import GameSwitcherBlock from "./GameSwitcherBlock";
import GameSwitcherDisplayConfig from "./GameSwitcherDisplayConfig";

const disposables: Disposable[] = [];

const FAT_CHESS_ACTIVITY_KEY = "bespoke:fat-chess.main";

/** 从 Redux 里取当前激活的活动菜单键（与 fat-stock 相同写法）。 */
const selectActivityMenuKey = (state: unknown): string | undefined => {
  if (state && typeof state === "object") {
    const frame = (state as { frame?: unknown }).frame;
    if (frame && typeof frame === "object") {
      const key = (frame as { activityMenuKey?: unknown }).activityMenuKey;
      if (typeof key === "string") return key;
    }
  }
  return undefined;
};

export async function activate(sdk: FatNotesPluginSDK): Promise<void> {
  // 1. 活动栏入口 → 打开主侧栏
  // 注意：不能传 primarySidebarViewId。宿主 SDK 的 registerPrimarySidebar
  // 固定注册 `<pluginId>.primarySidebar`，而宿主 useAppLayout 会用显式
  // primarySidebarViewId 去 registry 查（查不到就隐藏整个主侧栏），
  // fallback 只有在不传该字段时才会生效。参照 fat-stock 的写法。
  disposables.push(
    sdk.contributions.registerActivityBarItem({
      id: "fat-chess.main",
      title: "fat-chess 棋类游戏",
      icon: "Swords",
    }),
  );

  // 2. 主侧栏：棋种菜单（窄版）
  disposables.push(
    sdk.contributions.registerPrimarySidebar(() =>
      React.createElement(PluginView, { sdk, view: "menu" }),
    ),
  );

  // 3. 工作区：对局界面（id 与活动栏项一致，选中插件时宿主渲染）
  disposables.push(
    sdk.contributions.registerWorkbenchPage({
      id: "fat-chess.main",
      render: () => React.createElement(PluginView, { sdk, view: "workbench" }),
    }),
  );

  // 4. 设置页
  disposables.push(
    sdk.contributions.registerSettingsPage({
      id: "fat-chess.settings",
      title: "fat-chess 棋类游戏",
      render: () => React.createElement(PluginView, { sdk, view: "settings" }),
    }),
  );

  // 4. 命令：打开棋类大厅
  disposables.push(
    sdk.commands.register("fat-chess.open", async () => {
      sdk.ui.toast.info("fat-chess 已就绪，从左侧活动栏进入棋类游戏");
      return "ok";
    }),
  );

  // 5. 命令：同步下棋工具
  disposables.push(
    sdk.commands.register("fat-chess.sync-tools", async () => {
      const report = await syncMcpTools(sdk);
      if (!report.failed.length) {
        sdk.ui.toast.success(`已同步 ${report.ok} 个下棋 MCP 工具`);
      } else {
        sdk.ui.toast.warn(`同步完成：成功 ${report.ok}，失败 ${report.failed.length}`);
      }
      return report;
    }),
  );

  // 6. 仪表盘组件：「棋游」卡片（参考 fat-tools 的 blockType 注册方式）。
  //    挂在「其他(other)」分类下，卡片内可在多个棋种间切换并直接对局：
  //    参与切换的棋种 / 默认棋种 / 切换按钮显隐 / 按钮组或下拉框 / 顶或底，
  //    均由右侧「显示配置」面板（registerBlockDisplayConfig）配置。
  //    用 try/catch 兜底：宿主版本缺少该能力时不影响其余激活流程。
  try {
    disposables.push(
      sdk.contributions.registerBlockType({
        type: "fat-chess.game",
        title: "棋游",
        iconUrl: CHESS_GAME_ICON_URL,
        category: "other",
        index: 100,
        defaultSize: { w: 6, h: 30, minW: 4, minH: 16 },
        // 新建卡片写入 options 的默认值（宿主会深拷贝）
        defaultOptions: {
          gameSwitcher: {
            games: ["xiangqi", "gomoku", "go", "chess"],
            defaultGame: "xiangqi",
            showSwitch: true,
            switchStyle: "segmented",
            switchPosition: "top",
          },
        },
        render: (props) =>
          React.createElement(GameSwitcherBlock, {
            config: props.config,
            inConfig: props.inConfig,
            sdk,
          }),
      }),
    );
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn("[fat-chess] 注册「棋游」仪表盘组件失败：", e);
  }

  // 6.5 「棋游」卡片的显示配置面板（组件配置抽屉 > 显示配置）
  try {
    disposables.push(
      sdk.contributions.registerBlockDisplayConfig({
        id: "fat-chess.game.config",
        blockType: "fat-chess.game",
        render: () => React.createElement(GameSwitcherDisplayConfig, { sdk }),
      }),
    );
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn("[fat-chess] 注册「棋游」显示配置面板失败：", e);
  }

  // 7. 选中 fat-chess 时隐藏次侧栏（聊天）与底部面板，给棋盘更大空间。
  let hideSecondarySidebarDisposable: Disposable | null = null;
  let hidePanelDisposable: Disposable | null = null;
  const syncHideOnActivePage = (activeKey: string | undefined): void => {
    const shouldHide = activeKey === FAT_CHESS_ACTIVITY_KEY;
    if (shouldHide) {
      if (!hideSecondarySidebarDisposable) {
        hideSecondarySidebarDisposable =
          sdk.contributions.registerHideSecondarySidebar();
      }
      if (!hidePanelDisposable) {
        hidePanelDisposable = sdk.contributions.registerHidePanel();
      }
    } else {
      if (hideSecondarySidebarDisposable) {
        hideSecondarySidebarDisposable.dispose();
        hideSecondarySidebarDisposable = null;
      }
      if (hidePanelDisposable) {
        hidePanelDisposable.dispose();
        hidePanelDisposable = null;
      }
    }
  };
  syncHideOnActivePage(sdk.store.select(selectActivityMenuKey));
  disposables.push(
    sdk.store.subscribe(selectActivityMenuKey, (nextKey) =>
      syncHideOnActivePage(nextKey),
    ),
  );
  disposables.push({
    dispose() {
      if (hideSecondarySidebarDisposable) {
        hideSecondarySidebarDisposable.dispose();
        hideSecondarySidebarDisposable = null;
      }
      if (hidePanelDisposable) {
        hidePanelDisposable.dispose();
        hidePanelDisposable = null;
      }
    },
  });

  // 8. 尽力同步下棋工具（失败不阻塞激活）
  try {
    const report = await syncMcpTools(sdk);
    if (report.failed.length) {
      // eslint-disable-next-line no-console
      console.warn("[fat-chess] MCP 工具同步部分失败", report.failed);
    }
  } catch (e) {
    // eslint-disable-next-line no-console
    console.warn("[fat-chess] MCP 工具同步失败", e);
  }
}

export function deactivate(): void {
  while (disposables.length) {
    try {
      disposables.pop()?.dispose();
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn("[fat-chess] dispose error", e);
    }
  }
}
