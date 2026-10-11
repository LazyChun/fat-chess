/*
 * 「棋游」仪表盘卡片图标（内联 SVG data-URI）
 *
 * 宿主添加组件菜单把 iconUrl 直接塞进 <img src>，插件静态资源没有
 * 独立公开根路径，相对/绝对路径都会 404，因此用 data-URI 内联最可靠
 * （与 fat-tools/src/assets/toolSwitcherIcon.ts 相同做法）。
 */

const CHESS_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
  <rect x="4" y="4" width="40" height="40" rx="10" fill="#722ed1"/>
  <path d="M24 11c-3.5 0-6 2.6-6 5.6 0 1.6.7 3 1.9 4L18 24h12l-1.9-3.4c1.2-1 1.9-2.4 1.9-4 0-3-2.5-5.6-6-5.6z" fill="#ffffff"/>
  <rect x="17" y="25.5" width="14" height="3.4" rx="1.7" fill="#ffffff" opacity="0.95"/>
  <rect x="15.5" y="31.5" width="17" height="3.6" rx="1.8" fill="#ffffff"/>
  <rect x="13.5" y="37" width="21" height="3.4" rx="1.7" fill="#ffffff" opacity="0.9"/>
</svg>`;

export const CHESS_GAME_ICON_URL = `data:image/svg+xml;utf8,${encodeURIComponent(
  CHESS_SVG,
)}`;
