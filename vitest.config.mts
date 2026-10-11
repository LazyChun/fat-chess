/**
 * Vitest 前端纯函数测试配置
 *
 * @author AgentCode
 * @date 2026-09-02
 */

import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
});