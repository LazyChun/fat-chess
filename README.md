# fat-chess 肥棋

FatNotes 的棋类游戏插件：**围棋 / 五子棋 / 中国象棋 / 国际象棋 / 斗兽棋 / 军棋（明盘）**，
支持三种对战模式：**人机对战**（本地 AI）、**对战大模型**（大模型通过宿主 MCP 下棋工具落子）、**本机双人**。

## 功能总览

| 棋种 | 坐标（列 a..，行 0.. 自上而下） | 规则要点 |
| --- | --- | --- |
| 围棋 go | 单点坐标（如 `j7`），`pass` 虚着 | 9/13/19 路可选；气尽提子、禁自杀与劫；双虚着终局数空；黑贴 6.5 目 |
| 五子棋 gomoku | 单点坐标（15×15） | 任意方向五连（含长连）即胜 |
| 中国象棋 xiangqi | `fromto`（如 `b0c2`） | 红先黑后；蹩马腿、塞象眼、炮架、过河兵、飞将、应将、将死/困毙 |
| 国际象棋 chess | UCI `fromto`（`e7e8q` 升变） | 白先黑后；易位、吃过路兵、升变、将死、逼和、50 回合、三次重复 |
| 斗兽棋 jungle | `fromto` | 蓝先红后；象>狮>虎>豹>狼>狗>猫>鼠、鼠吃象；兽穴制胜、行营免疫、陷阱吃子、狮虎跳河 |
| 军棋（明盘）junqi | `fromto` | 黑先红后；军衔吃子、工兵挖雷、炸弹同归于尽、军旗被吃即负、大本营禁移 |

颜色语义：0=先手，1=后手（围棋/五子棋黑=0，象棋红=0，国际象棋白=0，斗兽棋蓝=0，军棋黑=0）。

## 对战模式

- **人机对战**：本地 alpha-beta 搜索（吃子排序、深度按难度映射），AI 难度 1-3 级。
- **对战大模型**：插件自动把 6×5=30 个“下棋工具”注册为宿主的 requestUrl MCP 工具，
  大模型走子时由后端编排 `ai.chat`（toolIds + 最多 12 轮工具迭代），模型通过工具回调
  插件后端内置的本地 HTTP 桥（`127.0.0.1:<随机端口>`）落子。
- **本机双人**：同一界面交替落子。

## 目录结构

```
fat-chess/
├── plugin.json                  # 宿主安装清单（id/mfName/backend 开关）
├── package.json                 # 前端依赖（react 18.2.0 / antd 6.3.1 与宿主 singleton 对齐）
├── webpack.config.js            # Module Federation 构建（勿改动共享版本）
├── src/                         # 前端
│   ├── index.tsx                # activate/deactivate：侧栏、设置页、命令、同步工具
│   ├── PluginView.tsx           # 大厅⇄对局路由 + 全局配置
│   ├── Lobby.tsx                # 棋种/模式/难度/模型选择
│   ├── GameView.tsx             # 对局界面：走子交互、悔棋/认输/重开、AI/大模型驱动
│   ├── boards.tsx               # 六种棋 SVG 棋盘渲染
│   ├── mcp.ts                   # 30 个下棋工具注册（addTool/editTool 幂等）
│   ├── api.ts / types.ts / games.ts
│   └── bootstrap.ts             # MF 异步入口（勿改）
├── backend/                     # Python 后端（零第三方依赖）
│   ├── main.py                  # JSON-RPC 入口：注册 handler + 惰性启动 HTTP 桥
│   ├── plugin_runtime.py        # 宿主 RPC 运行时（stdin/stdout 协议）
│   ├── engines/
│   │   ├── base.py              # GameBase/GameSession/SessionStore/坐标工具
│   │   ├── {go,gomoku,xiangqi,chess,jungle,junqi}.py  # 六引擎（完整规则）
│   │   ├── ai.py                # 统一 alpha-beta 搜索 + 六棋种评估
│   │   ├── service.py           # handle_rpc 动作分发 + llm_move 编排（_thinking 防重入）
│   │   └── bridge.py            # ThreadingHTTPServer 本地桥（MCP 工具回调）
│   └── tests/
│       ├── test_engines.py      # 34 个单元测试（python -m unittest tests.test_engines）
│       └── smoke_runtime.py     # 运行时冒烟：RPC + HTTP 桥全链路
└── install.zip                  # 构建产物（plugin.json + dist/* 平铺）
```

## 开发

```powershell
# 后端测试（34 用例 + 运行时冒烟）
Set-Location backend
python -m unittest tests.test_engines
python tests\smoke_runtime.py

# 前端
npm install            # 若 npm 10 arborist 报 edgesOut 崩溃，用 npx npm@11 install
npm run typecheck
npm run build          # 产物在 dist/（remoteEntry.js）
```

## 安装

1. `npm run build` 后，根目录 `install.zip` 已包含 `plugin.json` 与 `dist/*`（平铺）。
2. FatNotes → 扩展 → 自定义插件 → 新建插件，上传 `install.zip`。
3. 安装后从左侧活动栏进入「fat-chess 棋类游戏」；侧栏顶部「同步下棋工具」可随时刷新
   30 个 MCP 工具（桥端口变化后自动 editTool 更新 URL）。
4. 对战大模型前：在宿主 AI 设置中配置模型，并在插件设置页选择默认模型
   （或对局时在大厅下拉选择）。

> **模块联邦名称对齐**：宿主按插件 UUID 期望 MF 名 `plugin_<uuid>_...`。若宿主分配的
> UUID 与 `plugin.json` 的 `mfName` 不一致，请把宿主插件列表中的 UUID 更新到
> `plugin.json` 的 `mfName` 后重新 `npm run build`，否则会报
> `remoteEntryExports is undefined`。

## 大模型对战原理

```
用户落子 ──► 后端 llm_move（fatchess_llm_move handler）
                 │
                 ├─ host_call("ai.chat", {modelId, messages(含文字棋盘+规则),
                 │                        toolIds: fatchess_<game>_*,
                 │                        maxIterations: 12})
                 │
                 ▼
          宿主 aiService 多次迭代 ──► agent 工具层调用 requestUrl 工具
                 │                        POST http://127.0.0.1:<bridgePort>/fatchess/<game>/<action>
                 ▼
          插件后端 HTTP 桥 ──► handle_rpc（与 JSON-RPC 共用 SessionStore，状态同步）
                 │
                 ▼
          大模型落子成功 ──► 前端刷新局面
```

- 工具回调走 HTTP 桥线程，不持有 RPC 全局锁；`_thinking` 集合防止重复触发。
- 对局状态天然同步：JSON-RPC 与 HTTP 桥共享同一 `SessionStore`。

## 已知边界

- 宿主 secondary 侧栏为聊天保留，插件只能使用 primary 侧栏。
- LLM 走子耗时约十几秒到一分钟（由模型与迭代次数决定）。
- 军棋为明盘变体（暗棋需要状态加密与裁判服务，超出当前范围）。
