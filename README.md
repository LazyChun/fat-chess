# fat-chess

肥棋，棋盘游戏集合

A FatNotes bespoke plugin scaffolded by `fat-notes-extension-cli`.

## Install dependencies

```
npm install
```

## Build

```
npm run build
```

The production bundle (including `remoteEntry.js`) is emitted to `dist/`.

## Package & install

Zip the **contents** of `dist/` together with the top-level `plugin.json` as
`install.zip` and install it via FatNotes → Extensions → Custom Bespoke Plugins.

## Module Federation name alignment

FatNotes assigns each plugin a UUID at install time. The Module Federation
remote name the host expects is `plugin_<uuid_with_underscores>`. After
installing or registering the plugin in FatNotes:

1. Find the assigned UUID in the host plugin list (e.g. `2c535311-9c1a-4126-8921-ddfac4f5f690`).
2. Add `"mfName": "plugin_2c535311_9c1a_4126_8921_ddfac4f5f690"` to your **workspace** `plugin.json`.
3. Rebuild (`npm run build`). The webpack config picks up `mfName` automatically.

Alternatively, set the env var before building:

```powershell
$env:PLUGIN_MF_NAME = "plugin_2c535311_9c1a_4126_8921_ddfac4f5f690"
npm run dev
```

If names don't match you will see:

> `[ Federation Runtime ]: remoteEntryExports is undefined`

## File structure

- `src/index.tsx` — plugin entry; must export `activate(sdk)` and `deactivate()`.
- `src/PluginView.tsx` — example contribution component.
- `plugin.json` — manifest consumed by the FatNotes installer.
- `types/fat-notes-sdk.d.ts` — SDK type declarations (mirror of host).
- `webpack.config.js` — Module Federation build (`exposes ./plugin`).

## SDK capabilities

- `sdk.dataSource` — list / read data sources
- `sdk.query` / `sdk.mutation` — run saved queries/mutations or raw SQL
- `sdk.ui` — toast, modal, theme, i18n
- `sdk.commands` — register/execute commands
- `sdk.store` — read host Redux state
- `sdk.contributions` — activityBar / primary sidebar / panel / footer / routes / block types
- `sdk.events` — host/plugin event bus
- `sdk.remoteComponents.PluginBlockBox` — 远程组件（主程序暴露）用于渲染卡片盒
- `sdk.boards` — 高级插件板卡配置读写：
  - `getBoard/setBoard` -> `templates/default/confs/boards/<唯一key>/file.json`
  - `getDependencies/setDependencies` -> `templates/default/confs/boards/<唯一key>/dependencies.json`
  - `addConfigCard` -> 开发模式可配合浮动按钮快速新增配置卡片

> The **secondary sidebar** is reserved for FatNotes' chat block and is not
> available to plugins.
