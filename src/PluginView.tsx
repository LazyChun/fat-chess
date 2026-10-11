/*
 * Plugin board config demo:
 * - Uses host remote component sdk.remoteComponents.PluginBlockBox
 * - Saves board config under confs/boards/<uniqueKey>/file.json
 * - Saves dependencies under confs/boards/<uniqueKey>/dependencies.json
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import type {
  FatNotesPluginSDK,
  PluginBoardDependency,
  PluginBlockBoxBoardApi,
} from "fat-notes-sdk";

interface Props {
  sdk: FatNotesPluginSDK;
}

const PluginView: React.FC<Props> = ({ sdk }) => {
  const [boardMeta, setBoardMeta] = useState<Record<string, unknown>>({});
  const [blocks, setBlocks] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const uniqueKey = "default";
  const PluginBlockBox = sdk.remoteComponents.PluginBlockBox;
  const isDevMode = sdk.host.mode === "dev";

  const loadBoard = useCallback(async () => {
    setLoading(true);
    try {
      const [conf, deps, boxBlocks] = await Promise.all([
        sdk.boards.getBoard<Record<string, unknown>>(uniqueKey),
        sdk.boards.getDependencies(uniqueKey),
        sdk.boards.getBoardBlocks(uniqueKey),
      ]);
      setBoardMeta(conf || {});
      setBlocks(boxBlocks || []);
    } catch (e) {
      sdk.ui.toast.error(`Load board failed: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [sdk]);

  const addConfigCard = useCallback(async () => {
    if (!isDevMode) return;
    setSaving(true);
    try {
      const dep: PluginBoardDependency = {
        id: "fat-chess.widget-runtime",
        type: "feature",
        version: sdk.host.version,
      };
      await sdk.boards.addConfigCard(uniqueKey, {
        title: "New Config Card",
        type: "text",
        dependencies: [dep],
      });
      await loadBoard();
      sdk.ui.toast.success("Added config card");
    } catch (e) {
      sdk.ui.toast.error(`Add config card failed: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  }, [isDevMode, loadBoard, sdk]);

  const saveMeta = useCallback(async () => {
    setSaving(true);
    try {
      const next = {
        ...boardMeta,
        uniqueKey,
        pluginId: sdk.pluginId,
        lastSavedAt: Date.now(),
      };
      const saved = await sdk.boards.setBoard(uniqueKey, next, { merge: true });
      setBoardMeta(saved || next);
      sdk.ui.toast.success("Saved board meta");
    } catch (e) {
      sdk.ui.toast.error(`Save board meta failed: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  }, [boardMeta, sdk]);

  useEffect(() => {
    loadBoard();
  }, [loadBoard]);

  const boardId = useMemo(() => {
    return `plugin:${sdk.pluginId}:${uniqueKey}`;
  }, [boardMeta, sdk.pluginId]);
  const boardApi = useMemo<PluginBlockBoxBoardApi>(
    () => ({
      loadBoard: async () => {
        const detail = await sdk.boards.getBoardDetail(uniqueKey);
        return {
          name: detail.name,
          type: detail.type,
          blocks: detail.blocks,
        };
      },
      saveBoard: async (input) => {
        const detail = await sdk.boards.saveBoardDetail(uniqueKey, input);
        setBoardMeta(detail.config || {});
        setBlocks(detail.blocks || []);
        return detail;
      },
      createCard: (block) => sdk.boards.createBlock(uniqueKey, block),
      updateCard: (block) => sdk.boards.updateBlock(uniqueKey, block),
      deleteCard: (blockId) => sdk.boards.deleteBlock(uniqueKey, blockId),
    }),
    [sdk, uniqueKey],
  );

  return (
    <div style={{ position: "relative" }}>
      <PluginBlockBox
        blocks={blocks}
        boardId={boardId}
        minHeight={280}
        boardApi={boardApi}
      />
    </div>
  );
};

export default PluginView;
