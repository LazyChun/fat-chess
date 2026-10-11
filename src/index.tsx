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
