/**
 * 六种棋的 SVG 棋盘渲染与走子交互。
 *
 * 坐标：列 a..（左→右），行 0..（上→下）；单元格 (row, col)。
 * - 落子类（go/gomoku）：点击空白交叉点落子。
 * - 走子类（chess/xiangqi/jungle/junqi）：先点己方棋子，再点目标格。
 */
import React, { useMemo, useState } from "react";
import type { GameState } from "./types";
import {
  CHESS_GLYPHS,
  GAME_MAP,
  JUNGLE_DENS,
  JUNGLE_NAMES,
  JUNGLE_RIVER,
  JUNGLE_TRAPS,
  JUNQI_CAMPS,
  JUNQI_FORTS,
  JUNQI_NAMES,
  XQ_PIECE_NAMES,
  colLetter,
  isEmptyCell,
  sqText,
} from "./games";

interface BoardProps {
  state: GameState;
  legalMoves?: string[];
  selected?: string | null;
  interactive: boolean;
  onPlacementMove?: (sq: string) => void;
  onMove?: (from: string, to: string) => void;
  onSelect?: (sq: string | null) => void;
}

const COLORS = {
  wood: "#e8b96a",
  woodDark: "#c8954a",
  line: "#5a3a1a",
  black: "#111",
  white: "#f8f8f8",
  red: "#c62828",
  blue: "#1565c0",
  gray: "#666",
};

function cellColor(r: number, c: number): string {
  return (r + c) % 2 === 0 ? "#f0d9b5" : "#b58863";
}

export const ChessBoard: React.FC<BoardProps> = (props) => {
  const { state, legalMoves, selected, interactive, onMove, onSelect } = props;
  const N = 8;
  const cell = 60;
  const size = N * cell;

  const targets = useMemo(() => {
    const s = new Set<string>();
    if (selected && legalMoves) {
      for (const m of legalMoves) {
        if (m.startsWith(selected) && m.length >= 4) s.add(m.slice(2, 4));
      }
    }
    return s;
  }, [selected, legalMoves]);

  const click = (r: number, c: number) => {
    if (!interactive) return;
    const sq = sqText(r, c);
    const v = state.board[r]?.[c];
    const own = !isEmptyCell(v) && ((state.turn === 0 && String(v) === String(v).toUpperCase()) || (state.turn === 1 && String(v) === String(v).toLowerCase()));
    if (!selected) {
      if (own) onSelect?.(sq);
      return;
    }
    if (sq === selected) {
      onSelect?.(null);
      return;
    }
    if (targets.has(sq)) {
      onMove?.(selected, sq);
      onSelect?.(null);
      return;
    }
    if (own) {
      onSelect?.(sq);
      return;
    }
    onSelect?.(null);
  };

  return (
    <svg width={size} height={size} style={{ maxWidth: "100%" }}>
      {Array.from({ length: N }, (_, r) =>
        Array.from({ length: N }, (_, c) => (
          <rect
            key={`${r}-${c}`}
            x={c * cell}
            y={r * cell}
            width={cell}
            height={cell}
            fill={cellColor(r, c)}
            stroke="#00000022"
            onClick={() => click(r, c)}
            style={{ cursor: interactive ? "pointer" : "default" }}
          />
        )),
      )}
      {/* 坐标标签 */}
      {Array.from({ length: N }, (_, c) => (
        <text key={`c${c}`} x={c * cell + cell / 2} y={size - 3} fontSize={10} textAnchor="middle" fill="#00000055">
          {colLetter(c)}
        </text>
      ))}
      {Array.from({ length: N }, (_, r) => (
        <text key={`r${r}`} x={3} y={r * cell + cell / 2 + 3} fontSize={10} fill="#00000055">
          {8 - r}
        </text>
      ))}
      {/* 上一步 */}
      {state.lastMove && state.lastMove.length >= 4 && (
        <>
          <LastMark x={xOf(state.lastMove, 0, cell)} y={yOf(state.lastMove, 1, cell)} cell={cell} />
          <LastMark x={xOf(state.lastMove, 2, cell)} y={yOf(state.lastMove, 3, cell)} cell={cell} />
        </>
      )}
      {/* 选中 */}
      {selected && (
        <rect
          x={colOf(selected) * cell}
          y={rowOf(selected) * cell}
          width={cell}
          height={cell}
          fill="#ffeb3b55"
          stroke="#f9a825"
          strokeWidth={2}
        />
      )}
      {/* 合法目标 */}
      {selected &&
        Array.from(targets).map((t) => (
          <circle
            key={t}
            cx={colOf(t) * cell + cell / 2}
            cy={rowOf(t) * cell + cell / 2}
            r={7}
            fill="#4caf5055"
            stroke="#2e7d32"
          />
        ))}
      {/* 棋子 */}
      {state.board.map((row, r) =>
        row.map((v, c) => {
          if (isEmptyCell(v)) return null;
          const g = CHESS_GLYPHS[String(v)];
          const white = String(v) === String(v).toUpperCase();
          return (
            <g key={`${r}-${c}`} onClick={() => click(r, c)} style={{ cursor: interactive ? "pointer" : "default" }}>
              <text
                x={c * cell + cell / 2}
                y={r * cell + cell / 2 + 8}
                fontSize={40}
                textAnchor="middle"
                fill={white ? "#fff" : "#111"}
                stroke={white ? "#111" : "none"}
                strokeWidth={white ? 1.2 : 0}
              >
                {g || String(v)}
              </text>
            </g>
          );
        }),
      )}
    </svg>
  );
};

export const XiangqiBoard: React.FC<BoardProps> = (props) => {
  const { state, legalMoves, selected, interactive, onMove, onSelect } = props;
  const rows = state.rows || 10;
  const cols = state.cols || 9;
  const cell = 54;
  const sizeW = cols * cell;
  const sizeH = rows * cell;

  const targets = useMemo(() => {
    const s = new Set<string>();
    if (selected && legalMoves) {
      for (const m of legalMoves) {
        if (m.startsWith(selected) && m.length >= 4) s.add(m.slice(2, 4));
      }
    }
    return s;
  }, [selected, legalMoves]);

  const click = (r: number, c: number) => {
    if (!interactive) return;
    const sq = sqText(r, c);
    const v = state.board[r]?.[c];
    const own = !isEmptyCell(v) && ((state.turn === 0 && String(v) === String(v).toUpperCase()) || (state.turn === 1 && String(v) === String(v).toLowerCase()));
    if (!selected) {
      if (own) onSelect?.(sq);
      return;
    }
    if (sq === selected) {
      onSelect?.(null);
      return;
    }
    if (targets.has(sq)) {
      onMove?.(selected, sq);
      onSelect?.(null);
      return;
    }
    if (own) {
      onSelect?.(sq);
      return;
    }
    onSelect?.(null);
  };

  const px = (c: number) => c * cell + cell / 2;
  const py = (r: number) => r * cell + cell / 2;

  return (
    <svg width={sizeW} height={sizeH} style={{ maxWidth: "100%" }}>
      <rect x={0} y={0} width={sizeW} height={sizeH} fill={COLORS.wood} />
      {/* 网格线 */}
      {Array.from({ length: cols }, (_, c) => (
        <line key={`v${c}`} x1={px(c)} y1={0} x2={px(c)} y2={sizeH} stroke={COLORS.line} strokeWidth={1.2} />
      ))}
      {Array.from({ length: rows }, (_, r) => (
        <g key={`h${r}`}>
          <line
            x1={0}
            y1={py(r)}
            x2={sizeW}
            y2={py(r)}
            stroke={COLORS.line}
            strokeWidth={1.2}
            strokeDasharray={r === 4 || r === 5 ? "8 6" : undefined}
          />
          {/* 楚河汉界 */}
          {r === 5 && (
            <text x={sizeW / 2} y={py(r) - 12} fontSize={20} fill="#8d5b24" textAnchor="middle" opacity={0.85}>
              楚 河 汉 界
            </text>
          )}
        </g>
      ))}
      {/* 九宫斜线 */}
      {(() => {
        const lo = 0;
        const hi = 2;
        return (
          <>
            <line x1={px(3)} y1={py(lo)} x2={px(5)} y2={py(hi)} stroke={COLORS.line} strokeWidth={1.2} />
            <line x1={px(5)} y1={py(lo)} x2={px(3)} y2={py(hi)} stroke={COLORS.line} strokeWidth={1.2} />
            <line x1={px(3)} y1={py(rows - 1 - hi)} x2={px(5)} y2={py(rows - 1 - lo)} stroke={COLORS.line} strokeWidth={1.2} />
            <line x1={px(5)} y1={py(rows - 1 - hi)} x2={px(3)} y2={py(rows - 1 - lo)} stroke={COLORS.line} strokeWidth={1.2} />
          </>
        );
      })()}
      {/* 兵位/炮位标记 */}
      {[
        [3, 0],
        [3, 2],
        [3, 4],
        [3, 6],
        [3, 8],
        [6, 0],
        [6, 2],
        [6, 4],
        [6, 6],
        [6, 8],
      ].map(([r, c]) => (
        <g key={`mark${r}-${c}`}>
          <line x1={px(c) - 6} y1={py(r)} x2={px(c) + 6} y2={py(r)} stroke={COLORS.line} />
          <line x1={px(c)} y1={py(r) - 6} x2={px(c)} y2={py(r) + 6} stroke={COLORS.line} />
        </g>
      ))}
      {/* 上一步 */}
      {state.lastMove && state.lastMove.length >= 4 && (
        <>
          <LastMark x={px(colOf(state.lastMove))} y={py(rowOf(state.lastMove))} cell={cell} />
          <LastMark x={px(colOf(state.lastMove, 2))} y={py(rowOf(state.lastMove, 3))} cell={cell} />
        </>
      )}
      {selected && (
        <circle cx={px(colOf(selected))} cy={py(rowOf(selected))} r={22} fill="#ffeb3b55" stroke="#f9a825" strokeWidth={2} />
      )}
      {selected &&
        Array.from(targets).map((t) => (
          <circle key={t} cx={px(colOf(t))} cy={py(rowOf(t))} r={8} fill="#4caf5055" stroke="#2e7d32" />
        ))}
      {state.board.map((row, r) =>
        row.map((v, c) => {
          if (isEmptyCell(v)) return null;
          const isRed = String(v) === String(v).toUpperCase();
          const name = XQ_PIECE_NAMES[String(v)] || String(v);
          return (
            <g key={`${r}-${c}`} onClick={() => click(r, c)} style={{ cursor: interactive ? "pointer" : "default" }}>
              <circle cx={px(c)} cy={py(r)} r={20} fill={isRed ? "#ffcdd2" : "#e0e0e0"} stroke={COLORS.line} strokeWidth={1.5} />
              <text x={px(c)} y={py(r) + 6} fontSize={20} textAnchor="middle" fill={isRed ? COLORS.red : "#111"}>
                {name}
              </text>
            </g>
          );
        }),
      )}
    </svg>
  );
};

export const JungleBoard: React.FC<BoardProps> = (props) => {
  const { state, legalMoves, selected, interactive, onMove, onSelect } = props;
  const rows = state.rows || 7;
  const cols = state.cols || 9;
  const cell = 56;
  const sizeW = cols * cell;
  const sizeH = rows * cell;

  const targets = useMemo(() => {
    const s = new Set<string>();
    if (selected && legalMoves) {
      for (const m of legalMoves) {
        if (m.startsWith(selected) && m.length >= 4) s.add(m.slice(2, 4));
      }
    }
    return s;
  }, [selected, legalMoves]);

  const click = (r: number, c: number) => {
    if (!interactive) return;
    const sq = sqText(r, c);
    const v = state.board[r]?.[c];
    const own = !isEmptyCell(v) && ((state.turn === 0 && String(v) === String(v).toUpperCase()) || (state.turn === 1 && String(v) === String(v).toLowerCase()));
    if (!selected) {
      if (own) onSelect?.(sq);
      return;
    }
    if (sq === selected) {
      onSelect?.(null);
      return;
    }
    if (targets.has(sq)) {
      onMove?.(selected, sq);
      onSelect?.(null);
      return;
    }
    if (own) {
      onSelect?.(sq);
      return;
    }
    onSelect?.(null);
  };

  const px = (c: number) => c * cell + cell / 2;
  const py = (r: number) => r * cell + cell / 2;

  const isRiver = (r: number, c: number) => JUNGLE_RIVER.some(([rr, cc]) => rr === r && cc === c);
  const isDen = (r: number, c: number) => JUNGLE_DENS.some(([rr, cc]) => rr === r && cc === c);
  const isTrap = (r: number, c: number) => JUNGLE_TRAPS.flat().some(([rr, cc]) => rr === r && cc === c);

  return (
    <svg width={sizeW} height={sizeH} style={{ maxWidth: "100%" }}>
      <rect x={0} y={0} width={sizeW} height={sizeH} fill={COLORS.wood} />
      {Array.from({ length: rows }, (_, r) =>
        Array.from({ length: cols }, (_, c) => {
          let fill = "transparent";
          if (isRiver(r, c)) fill = "#64b5f6";
          else if (isDen(r, c)) fill = "#ff8a65";
          else if (isTrap(r, c)) fill = "#ffd54f";
          if (fill !== "transparent") {
            return <rect key={`${r}-${c}`} x={px(c) - cell / 2 + 4} y={py(r) - cell / 2 + 4} width={cell - 8} height={cell - 8} rx={8} fill={fill} opacity={0.6} />;
          }
          return null;
        }),
      )}
      {Array.from({ length: cols }, (_, c) => (
        <line key={`v${c}`} x1={px(c)} y1={0} x2={px(c)} y2={sizeH} stroke={COLORS.line} strokeWidth={1.1} />
      ))}
      {Array.from({ length: rows }, (_, r) => (
        <line key={`h${r}`} x1={0} y1={py(r)} x2={sizeW} y2={py(r)} stroke={COLORS.line} strokeWidth={1.1} />
      ))}
      {state.lastMove && state.lastMove.length >= 4 && (
        <>
          <LastMark x={px(colOf(state.lastMove))} y={py(rowOf(state.lastMove))} cell={cell} />
          <LastMark x={px(colOf(state.lastMove, 2))} y={py(rowOf(state.lastMove, 3))} cell={cell} />
        </>
      )}
      {selected && (
        <circle cx={px(colOf(selected))} cy={py(rowOf(selected))} r={24} fill="#ffeb3b55" stroke="#f9a825" strokeWidth={2} />
      )}
      {selected &&
        Array.from(targets).map((t) => (
          <circle key={t} cx={px(colOf(t))} cy={py(rowOf(t))} r={9} fill="#4caf5055" stroke="#2e7d32" />
        ))}
      {state.board.map((row, r) =>
        row.map((v, c) => {
          if (isEmptyCell(v)) return null;
          const isBlue = String(v) === String(v).toUpperCase();
          const name = JUNGLE_NAMES[String(v)] || String(v);
          return (
            <g key={`${r}-${c}`} onClick={() => click(r, c)} style={{ cursor: interactive ? "pointer" : "default" }}>
              <circle cx={px(c)} cy={py(r)} r={20} fill={isBlue ? "#bbdefb" : "#ffcdd2"} stroke={isBlue ? COLORS.blue : COLORS.red} strokeWidth={1.6} />
              <text x={px(c)} y={py(r) + 6} fontSize={18} textAnchor="middle" fill={isBlue ? COLORS.blue : COLORS.red} fontWeight={600}>
                {name}
              </text>
            </g>
          );
        }),
      )}
    </svg>
  );
};

export const JunqiBoard: React.FC<BoardProps> = (props) => {
  const { state, legalMoves, selected, interactive, onMove, onSelect } = props;
  const rows = state.rows || 10;
  const cols = state.cols || 9;
  const cell = 52;
  const sizeW = cols * cell;
  const sizeH = rows * cell;

  const targets = useMemo(() => {
    const s = new Set<string>();
    if (selected && legalMoves) {
      for (const m of legalMoves) {
        if (m.startsWith(selected) && m.length >= 4) s.add(m.slice(2, 4));
      }
    }
    return s;
  }, [selected, legalMoves]);

  const click = (r: number, c: number) => {
    if (!interactive) return;
    const sq = sqText(r, c);
    const v = state.board[r]?.[c];
    const own = !isEmptyCell(v) && ((state.turn === 0 && String(v) === String(v).toUpperCase()) || (state.turn === 1 && String(v) === String(v).toLowerCase()));
    if (!selected) {
      if (own) onSelect?.(sq);
      return;
    }
    if (sq === selected) {
      onSelect?.(null);
      return;
    }
    if (targets.has(sq)) {
      onMove?.(selected, sq);
      onSelect?.(null);
      return;
    }
    if (own) {
      onSelect?.(sq);
      return;
    }
    onSelect?.(null);
  };

  const px = (c: number) => c * cell + cell / 2;
  const py = (r: number) => r * cell + cell / 2;

  const isCamp = (r: number, c: number) => JUNQI_CAMPS.flat().some(([rr, cc]) => rr === r && cc === c);
  const isFort = (r: number, c: number) => JUNQI_FORTS.flat().some(([rr, cc]) => rr === r && cc === c);
  const isRail = (r: number) => r >= 2 && r <= 7;

  return (
    <svg width={sizeW} height={sizeH} style={{ maxWidth: "100%" }}>
      <rect x={0} y={0} width={sizeW} height={sizeH} fill={COLORS.wood} />
      {/* 铁路/公路 */}
      {Array.from({ length: cols }, (_, c) => (
        <line key={`v${c}`} x1={px(c)} y1={0} x2={px(c)} y2={sizeH} stroke={COLORS.line} strokeWidth={1.1} />
      ))}
      {Array.from({ length: rows }, (_, r) => (
        <line key={`h${r}`} x1={0} y1={py(r)} x2={sizeW} y2={py(r)} stroke={COLORS.line} strokeWidth={1.1} strokeDasharray={isRail(r) ? "6 4" : undefined} />
      ))}
      {/* 行营 */}
      {JUNQI_CAMPS.flat().map(([r, c]) => (
        <rect key={`camp${r}-${c}`} x={px(c) - cell / 2 + 5} y={py(r) - cell / 2 + 5} width={cell - 10} height={cell - 10} rx={10} fill="#90caf955" stroke="#42a5f5" strokeWidth={1} />
      ))}
      {/* 大本营 */}
      {JUNQI_FORTS.flat().map(([r, c]) => (
        <rect key={`fort${r}-${c}`} x={px(c) - cell / 2 + 4} y={py(r) - cell / 2 + 4} width={cell - 8} height={cell - 8} rx={4} fill="#ffcc8055" stroke="#ef6c00" strokeWidth={1.2} />
      ))}
      {state.lastMove && state.lastMove.length >= 4 && (
        <>
          <LastMark x={px(colOf(state.lastMove))} y={py(rowOf(state.lastMove))} cell={cell} />
          <LastMark x={px(colOf(state.lastMove, 2))} y={py(rowOf(state.lastMove, 3))} cell={cell} />
        </>
      )}
      {selected && (
        <circle cx={px(colOf(selected))} cy={py(rowOf(selected))} r={22} fill="#ffeb3b55" stroke="#f9a825" strokeWidth={2} />
      )}
      {selected &&
        Array.from(targets).map((t) => (
          <circle key={t} cx={px(colOf(t))} cy={py(rowOf(t))} r={8} fill="#4caf5055" stroke="#2e7d32" />
        ))}
      {state.board.map((row, r) =>
        row.map((v, c) => {
          if (isEmptyCell(v)) return null;
          const isRed = String(v) === String(v).toLowerCase();
          const name = JUNQI_NAMES[String(v)] || String(v);
          const fontSize = name.length > 1 ? 13 : 16;
          return (
            <g key={`${r}-${c}`} onClick={() => click(r, c)} style={{ cursor: interactive ? "pointer" : "default" }}>
              <circle cx={px(c)} cy={py(r)} r={18} fill={isRed ? "#ffcdd2" : "#d7ccc8"} stroke={isRed ? COLORS.red : "#333"} strokeWidth={1.5} />
              <text x={px(c)} y={py(r) + 4} fontSize={fontSize} textAnchor="middle" fill={isRed ? COLORS.red : "#111"} fontWeight={600}>
                {name}
              </text>
            </g>
          );
        }),
      )}
    </svg>
  );
};

export const PlacementBoard: React.FC<BoardProps> = (props) => {
  const { state, legalMoves, selected, interactive, onPlacementMove } = props;
  const n = state.size || state.rows || 19;
  const cell = n > 9 ? 26 : 40;
  const size = n * cell + 20;

  const legalSet = useMemo(() => new Set(legalMoves || []), [legalMoves]);
  const last = state.lastMove;

  const click = (r: number, c: number) => {
    if (!interactive) return;
    const sq = sqText(r, c);
    if (isEmptyCell(state.board[r]?.[c])) onPlacementMove?.(sq);
  };

  return (
    <svg width={size} height={size} style={{ maxWidth: "100%" }}>
      <rect x={0} y={0} width={size} height={size} fill={COLORS.wood} />
      <g transform={`translate(10,10)`}>
        {Array.from({ length: n }, (_, i) => (
          <line key={`v${i}`} x1={i * cell} y1={0} x2={i * cell} y2={(n - 1) * cell} stroke={COLORS.line} strokeWidth={1} />
        ))}
        {Array.from({ length: n }, (_, i) => (
          <line key={`h${i}`} x1={0} y1={i * cell} x2={(n - 1) * cell} y2={i * cell} stroke={COLORS.line} strokeWidth={1} />
        ))}
        {/* 星位 */}
        {(() => {
          const stars: number[] = n === 19 ? [3, 9, 15] : n === 15 ? [3, 7, 11] : n === 13 ? [3, 6, 9] : n === 9 ? [2, 4, 6] : [2, n - 3];
          const marks: Array<[number, number]> = [];
          for (const a of stars) {
            for (const b of stars) {
              if (n <= 9 && a !== b) continue; // 9 路只留天元? 保留四星位
              marks.push([a, b]);
            }
          }
          if (n === 9) {
            return (
              <>
                <circle cx={cell * 2} cy={cell * 2} r={3} fill={COLORS.line} />
                <circle cx={cell * 6} cy={cell * 2} r={3} fill={COLORS.line} />
                <circle cx={cell * 2} cy={cell * 6} r={3} fill={COLORS.line} />
                <circle cx={cell * 6} cy={cell * 6} r={3} fill={COLORS.line} />
                <circle cx={cell * 4} cy={cell * 4} r={3} fill={COLORS.line} />
              </>
            );
          }
          return marks.map(([r, c]) => <circle key={`${r}-${c}`} cx={c * cell} cy={r * cell} r={3.4} fill={COLORS.line} />);
        })()}
        {/* 合法点（落子类：所有可落子点，半透明小点提示） */}
        {Array.from(legalSet).map((m) => (
          <circle key={`lm${m}`} cx={colOf(m) * cell} cy={rowOf(m) * cell} r={4.5} fill="#4caf5055" />
        ))}
        {/* 上一步 */}
        {last && !isEmptyCell(state.board[rowOf(last)]?.[colOf(last)]) && (
          <circle cx={colOf(last) * cell} cy={rowOf(last) * cell} r={5} fill="transparent" stroke="#f44336" strokeWidth={1.6} />
        )}
        {/* 棋子 */}
        {state.board.map((row, r) =>
          row.map((v, c) => {
            if (isEmptyCell(v)) return null;
            const color = Number(v) === 0 ? "#111" : "#fff";
            return (
              <g key={`${r}-${c}`} onClick={() => click(r, c)} style={{ cursor: interactive ? "pointer" : "default" }}>
                <circle cx={c * cell} cy={r * cell} r={cell * 0.42} fill={color} stroke="#333" strokeWidth={1.2} />
              </g>
            );
          }),
        )}
      </g>
    </svg>
  );
};

// ── 工具函数 ────────────────────────────────────────────────

function rowOf(sq: string, offset = 0): number {
  return parseInt(sq.slice(1 + offset), 10);
}
function colOf(sq: string, offset = 0): number {
  return sq.charCodeAt(offset) - 97;
}
function xOf(move: string, offset: number, cell: number): number {
  return (move.charCodeAt(offset) - 97) * cell + cell / 2;
}
function yOf(move: string, offset: number, cell: number): number {
  return parseInt(move.slice(offset + 1), 10) * cell + cell / 2;
}

const LastMark: React.FC<{ x: number; y: number; cell: number }> = ({ x, y }) => (
  <circle cx={x} cy={y} r={6} fill="none" stroke="#f44336" strokeWidth={2} />
);

/** 统一的棋盘分发：按棋种渲染对应棋盘 */
export const GameBoard: React.FC<BoardProps> = (props) => {
  const meta = GAME_MAP[props.state.game] || GAME_MAP.gomoku;
  if (meta.kind === "placement") {
    return <PlacementBoard {...props} />;
  }
  switch (meta.id) {
    case "chess":
      return <ChessBoard {...props} />;
    case "xiangqi":
      return <XiangqiBoard {...props} />;
    case "jungle":
      return <JungleBoard {...props} />;
    case "junqi":
      return <JunqiBoard {...props} />;
    default:
      return <PlacementBoard {...props} />;
  }
};
