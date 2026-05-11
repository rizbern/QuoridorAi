/* ═══════════════════════════════════════════════════════════
   game.js — Quoridor frontend
   Board: 9×9 cells, 8×8 wall slots between them.
   Internal 17×17 board coords ↔ display 9×9 cell coords.
   ═══════════════════════════════════════════════════════════ */

const API = 'http://localhost:8000';

// ── Canvas setup ─────────────────────────────────────────────
const bCanvas  = document.getElementById('board-canvas');
const oCanvas  = document.getElementById('overlay-canvas');
const bCtx     = bCanvas.getContext('2d');
const oCtx     = oCanvas.getContext('2d');

const CELLS    = 9;        // 9×9 playable grid
const CELL     = 62;       // px per cell
const GAP      = 10;       // px for wall slots
const PAD      = 18;       // board padding
const BOARD_PX = PAD * 2 + CELLS * CELL + (CELLS - 1) * GAP;

bCanvas.width  = oCanvas.width  = BOARD_PX;
bCanvas.height = oCanvas.height = BOARD_PX;

// ── Game state ────────────────────────────────────────────────
let state        = null;
let legalMoves   = [];   // [{board_row, board_col}]
let mode         = 'pawn';  // 'pawn' | 'wall-h' | 'wall-v'
let hoverCell    = null;    // {display_row, display_col} or {board_row, board_col}
let moveCount    = 0;

// ── CSS vars ──────────────────────────────────────────────────
const CSS = {
  bg:        '#0d0d0f',
  bg2:       '#141418',
  cell:      '#1a1a22',
  cellHover: '#252530',
  cellLegal: '#1e2e18',
  legalRing: '#6fcf3a',
  border:    '#2a2a35',
  border2:   '#3a3a48',
  wallH:     '#e05c3a',
  wallV:     '#a06cd5',
  wallPrev:  'rgba(255,255,255,0.12)',
  xColor:    '#e8d5a3',
  xGlow:     'rgba(232,213,163,0.25)',
  oColor:    '#7eb8d4',
  oGlow:     'rgba(126,184,212,0.25)',
  goalX:     'rgba(232,213,163,0.06)',
  goalO:     'rgba(126,184,212,0.06)',
  text:      '#e8e8f0',
  textDim:   '#6a6a80',
};

// ── Coord helpers ─────────────────────────────────────────────
// Cell (dr, dc) top-left in px
function cellXY(dr, dc) {
  const x = PAD + dc * (CELL + GAP);
  const y = PAD + dr * (CELL + GAP);
  return { x, y };
}
// Centre of a display cell
function cellCentre(dr, dc) {
  const { x, y } = cellXY(dr, dc);
  return { x: x + CELL / 2, y: y + CELL / 2 };
}
// px → display cell (returns null if not over a cell)
function pxToCell(px, py) {
  for (let r = 0; r < CELLS; r++) {
    for (let c = 0; c < CELLS; c++) {
      const { x, y } = cellXY(r, c);
      if (px >= x && px <= x + CELL && py >= y && py <= y + CELL)
        return { display_row: r, display_col: c };
    }
  }
  return null;
}
// px → wall slot: returns {board_row, board_col, orientation} or null
// H-wall slot: horizontal gap between rows r and r+1
// V-wall slot: vertical gap between cols c and c+1
function pxToWallSlot(px, py, orientation) {
  if (orientation === 'wall-h') {
    // Horizontal gaps: y between row r and r+1
    for (let r = 0; r < CELLS - 1; r++) {
      const { y: y1 } = cellXY(r, 0);
      const gapY = y1 + CELL;
      if (py >= gapY - 2 && py <= gapY + GAP + 2) {
        // Which column anchor? wall covers c and c+1 — anchor at c
        for (let c = 0; c < CELLS - 1; c++) {
          const { x } = cellXY(r, c);
          if (px >= x && px <= x + CELL + GAP + CELL) {
            // board anchor: H wall at (r*2+1, c*2)
            return { board_row: r * 2 + 1, board_col: c * 2, orientation: 'H' };
          }
        }
      }
    }
  } else {
    // Vertical gaps: x between col c and c+1
    for (let c = 0; c < CELLS - 1; c++) {
      const { x: x1 } = cellXY(0, c);
      const gapX = x1 + CELL;
      if (px >= gapX - 2 && px <= gapX + GAP + 2) {
        for (let r = 0; r < CELLS - 1; r++) {
          const { y } = cellXY(r, c);
          if (py >= y && py <= y + CELL + GAP + CELL) {
            // board anchor: V wall at (r*2, c*2+1)
            return { board_row: r * 2, board_col: c * 2 + 1, orientation: 'V' };
          }
        }
      }
    }
  }
  return null;
}

// ── Board rendering ───────────────────────────────────────────
function drawBoard() {
  if (!state) return;
  const ctx = bCtx;
  ctx.clearRect(0, 0, BOARD_PX, BOARD_PX);

  // Background
  ctx.fillStyle = CSS.bg2;
  ctx.fillRect(0, 0, BOARD_PX, BOARD_PX);

  // Goal row tints
  for (let c = 0; c < CELLS; c++) {
    // Row 8 = X goal (bottom display row = board row 16)
    const { x: xb, y: yb } = cellXY(8, c);
    ctx.fillStyle = CSS.goalX;
    ctx.fillRect(xb, yb, CELL, CELL);
    // Row 0 = O goal
    const { x: xt, y: yt } = cellXY(0, c);
    ctx.fillStyle = CSS.goalO;
    ctx.fillRect(xt, yt, CELL, CELL);
  }

  // Cells
  const board = state.board;
  const legalSet = new Set(legalMoves.map(m => `${m.board_row},${m.board_col}`));

  for (let r = 0; r < CELLS; r++) {
    for (let c = 0; c < CELLS; c++) {
      const { x, y } = cellXY(r, c);
      const br = r * 2, bc = c * 2;
      const isLegal = legalSet.has(`${br},${bc}`);

      // Cell bg
      ctx.beginPath();
      ctx.roundRect(x, y, CELL, CELL, 4);
      ctx.fillStyle = isLegal ? CSS.cellLegal : CSS.cell;
      ctx.fill();

      // Legal move indicator ring
      if (isLegal) {
        ctx.beginPath();
        ctx.roundRect(x + 1, y + 1, CELL - 2, CELL - 2, 4);
        ctx.strokeStyle = CSS.legalRing;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Coordinate dots
      if (!isLegal) {
        ctx.beginPath();
        ctx.arc(x + CELL / 2, y + CELL / 2, 1.5, 0, Math.PI * 2);
        ctx.fillStyle = CSS.border2;
        ctx.fill();
      }
    }
  }

  // Walls from state
  drawWalls(ctx, board);

  // Pawns
  const px = state.pawns;
  if (px.x) drawPawn(ctx, px.x.board_row / 2, px.x.board_col / 2, 'x');
  if (px.o) drawPawn(ctx, px.o.board_row / 2, px.o.board_col / 2, 'o');
}

function drawWalls(ctx, board) {
  // Parse 17x17 board for wall segments and render them as thick bars
  const rendered = new Set();

  for (let r = 0; r < 17; r++) {
    for (let c = 0; c < 17; c++) {
      const cell = board[r][c];
      if (cell !== '-' && cell !== '|') continue;
      const key = `${r},${c}`;
      if (rendered.has(key)) continue;

      if (cell === '-') {
        // Horizontal wall: odd row r, even cols c, c+1, c+2
        // Find start of this wall segment
        if (r % 2 !== 1) continue;
        if (c % 2 !== 0) continue;
        // anchor: board (r, c) → displayed between display rows r//2-1 and r//2
        // gap is between display row (r-1)/2 and display row (r+1)/2
        const dr = (r - 1) / 2;  // gap is below display row dr
        const dc = c / 2;         // display col start
        rendered.add(`${r},${c}`);
        rendered.add(`${r},${c+1}`);
        rendered.add(`${r},${c+2}`);

        // Wall spans from cellXY(dr, dc) bottom to cellXY(dr, dc+1) bottom
        const { x: x0, y: y0 } = cellXY(dr, dc);
        const { x: x1 }        = cellXY(dr, dc + 1);
        const wallY = y0 + CELL + 1;
        const wallH = GAP - 2;
        const wallW = (x1 + CELL) - x0;

        ctx.beginPath();
        ctx.roundRect(x0, wallY, wallW, wallH, 3);
        ctx.fillStyle = CSS.wallH;
        ctx.fill();
        // Glow
        ctx.shadowColor = CSS.wallH;
        ctx.shadowBlur  = 8;
        ctx.fill();
        ctx.shadowBlur  = 0;

      } else if (cell === '|') {
        // Vertical wall: even rows r, r+1, r+2 at odd col c
        if (c % 2 !== 1) continue;
        if (r % 2 !== 0) continue;
        const dr = r / 2;
        const dc = (c - 1) / 2;
        rendered.add(`${r},${c}`);
        rendered.add(`${r+1},${c}`);
        rendered.add(`${r+2},${c}`);

        const { x: x0, y: y0 } = cellXY(dr, dc);
        const { y: y1 }        = cellXY(dr + 1, dc);
        const wallX = x0 + CELL + 1;
        const wallW = GAP - 2;
        const wallH = (y1 + CELL) - y0;

        ctx.beginPath();
        ctx.roundRect(wallX, y0, wallW, wallH, 3);
        ctx.fillStyle = CSS.wallV;
        ctx.fill();
        ctx.shadowColor = CSS.wallV;
        ctx.shadowBlur  = 8;
        ctx.fill();
        ctx.shadowBlur  = 0;
      }
    }
  }
}

function drawPawn(ctx, dr, dc, player) {
  const { x, y } = cellXY(dr, dc);
  const cx = x + CELL / 2;
  const cy = y + CELL / 2;
  const r  = CELL * 0.34;
  const color = player === 'x' ? CSS.xColor : CSS.oColor;
  const glow  = player === 'x' ? CSS.xGlow  : CSS.oGlow;

  // Outer glow
  ctx.beginPath();
  ctx.arc(cx, cy, r + 6, 0, Math.PI * 2);
  ctx.fillStyle = glow;
  ctx.fill();

  // Shadow
  ctx.shadowColor = color;
  ctx.shadowBlur  = 14;

  // Pawn body
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  const grad = ctx.createRadialGradient(cx - r * 0.3, cy - r * 0.3, r * 0.1, cx, cy, r);
  grad.addColorStop(0, player === 'x' ? '#f5e9c8' : '#a8d4eb');
  grad.addColorStop(1, player === 'x' ? '#a07840' : '#3a7a9a');
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.shadowBlur = 0;

  // Label
  ctx.fillStyle = player === 'x' ? '#4a3010' : '#0d2030';
  ctx.font = `bold ${Math.round(CELL * 0.3)}px "Bebas Neue", sans-serif`;
  ctx.textAlign    = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(player.toUpperCase(), cx, cy + 1);
}

// ── Overlay (hover previews) ──────────────────────────────────
function drawOverlay() {
  oCtx.clearRect(0, 0, BOARD_PX, BOARD_PX);
  if (!state || state.winner || state.current_player !== 'x') return;

  if (mode === 'pawn' && hoverCell) {
    const { display_row: dr, display_col: dc } = hoverCell;
    const br = dr * 2, bc = dc * 2;
    const legalSet = new Set(legalMoves.map(m => `${m.board_row},${m.board_col}`));
    if (legalSet.has(`${br},${bc}`)) {
      const { x, y } = cellXY(dr, dc);
      oCtx.beginPath();
      oCtx.roundRect(x + 2, y + 2, CELL - 4, CELL - 4, 4);
      oCtx.fillStyle = 'rgba(111,207,58,0.18)';
      oCtx.fill();
      oCtx.strokeStyle = CSS.legalRing;
      oCtx.lineWidth = 2;
      oCtx.stroke();
    }
  }

  if ((mode === 'wall-h' || mode === 'wall-v') && hoverCell) {
    drawWallPreview(oCtx, hoverCell);
  }
}

function drawWallPreview(ctx, slot) {
  if (!slot || slot.orientation === undefined) return;
  const { board_row: br, board_col: bc, orientation } = slot;
  const color = orientation === 'H' ? CSS.wallH : CSS.wallV;

  if (orientation === 'H') {
    // anchor (br odd, bc even): display between rows br//2 - 0.5
    if (br % 2 !== 1 || bc % 2 !== 0) return;
    const dr = (br - 1) / 2;
    const dc = bc / 2;
    if (dr < 0 || dr >= CELLS - 1 || dc < 0 || dc >= CELLS - 1) return;

    const { x: x0, y: y0 } = cellXY(dr, dc);
    const { x: x1 }        = cellXY(dr, dc + 1);
    const wallY = y0 + CELL + 1;
    ctx.beginPath();
    ctx.roundRect(x0, wallY, (x1 + CELL) - x0, GAP - 2, 3);
    ctx.fillStyle = color + '80';
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  } else {
    if (br % 2 !== 0 || bc % 2 !== 1) return;
    const dr = br / 2;
    const dc = (bc - 1) / 2;
    if (dr < 0 || dr >= CELLS - 1 || dc < 0 || dc >= CELLS - 1) return;

    const { x: x0, y: y0 } = cellXY(dr, dc);
    const { y: y1 }        = cellXY(dr + 1, dc);
    const wallX = x0 + CELL + 1;
    ctx.beginPath();
    ctx.roundRect(wallX, y0, GAP - 2, (y1 + CELL) - y0, 3);
    ctx.fillStyle = color + '80';
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
}

// ── Mouse events ──────────────────────────────────────────────
oCanvas.style.pointerEvents = 'auto';

oCanvas.addEventListener('mousemove', (e) => {
  if (!state || state.winner || state.current_player !== 'x') return;
  const rect = oCanvas.getBoundingClientRect();
  const px = e.clientX - rect.left;
  const py = e.clientY - rect.top;

  if (mode === 'pawn') {
    hoverCell = pxToCell(px, py);
  } else {
    hoverCell = pxToWallSlot(px, py, mode);
  }
  drawOverlay();
});

oCanvas.addEventListener('mouseleave', () => {
  hoverCell = null;
  drawOverlay();
});

oCanvas.addEventListener('click', async (e) => {
  if (!state || state.winner || state.current_player !== 'x') return;
  const rect = oCanvas.getBoundingClientRect();
  const px = e.clientX - rect.left;
  const py = e.clientY - rect.top;

  if (mode === 'pawn') {
    const cell = pxToCell(px, py);
    if (!cell) return;
    await humanPawnMove(cell.display_row, cell.display_col);

  } else {
    const slot = pxToWallSlot(px, py, mode);
    if (!slot) return;
    await humanWallMove(slot.board_row, slot.board_col, slot.orientation);
  }
});

// ── API calls ─────────────────────────────────────────────────
async function fetchLegal() {
  try {
    const res = await fetch(`${API}/legal-moves`);
    const data = await res.json();
    legalMoves = data.moves || [];
  } catch { legalMoves = []; }
}

async function humanPawnMove(dr, dc) {
  try {
    const res = await fetch(`${API}/move/pawn`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_row: dr, display_col: dc }),
    });
    if (!res.ok) { addLog('Invalid move', 'log-x'); return; }
    state = await res.json();
    moveCount++;
    addLog(`X → (${dr},${dc}) move`, 'log-x');
    legalMoves = [];
    render();
    if (!state.winner) await aiTurn();
  } catch (err) { console.error(err); }
}

async function humanWallMove(br, bc, ori) {
  try {
    const res = await fetch(`${API}/move/wall`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ board_row: br, board_col: bc, orientation: ori }),
    });
    if (!res.ok) {
      const err = await res.json();
      addLog(`Wall invalid: ${err.detail || '?'}`, 'log-x');
      flashHint('Wall blocked or would trap a player');
      return;
    }
    state = await res.json();
    moveCount++;
    addLog(`X placed ${ori}-wall`, ori === 'H' ? 'log-wall' : 'log-wall-v');
    legalMoves = [];
    render();
    if (!state.winner) await aiTurn();
  } catch (err) { console.error(err); }
}

async function aiTurn() {
  setThinking(true);
  setTurnBar('CPU IS THINKING…', CSS.oColor);
  try {
    const res = await fetch(`${API}/move/ai`, { method: 'POST' });
    if (!res.ok) throw new Error('AI error');
    state = await res.json();
    moveCount++;
    const mv = state.ai_move;
    if (mv.type === 'pawn') {
      addLog(`O → (${mv.board_row / 2},${mv.board_col / 2}) move`, 'log-o');
    } else {
      addLog(`O placed ${mv.orientation}-wall`, mv.orientation === 'H' ? 'log-wall' : 'log-wall-v');
    }
    if (!state.winner) await fetchLegal();
    render();
  } catch (err) {
    console.error(err);
  } finally {
    setThinking(false);
    if (state && !state.winner) {
      setTurnBar('YOUR TURN');
    }
  }
}

async function newGame() {
  try {
    const res  = await fetch(`${API}/new-game`, { method: 'POST' });
    state      = await res.json();
    legalMoves = [];
    moveCount  = 0;
    hoverCell  = null;
    document.getElementById('log-entries').innerHTML = '';
    setMode('pawn');
    await fetchLegal();
    render();
    document.getElementById('win-overlay').classList.remove('visible');
    setTurnBar('YOUR TURN');
    addLog('New game started', 'log-x');
  } catch (err) { console.error(err); }
}

// ── UI helpers ────────────────────────────────────────────────
function setMode(m) {
  mode = m;
  ['btn-pawn', 'btn-wall-h', 'btn-wall-v'].forEach(id =>
    document.getElementById(id).classList.remove('active'));
  const map = { 'pawn': 'btn-pawn', 'wall-h': 'btn-wall-h', 'wall-v': 'btn-wall-v' };
  document.getElementById(map[m]).classList.add('active');
  hoverCell = null;
  drawOverlay();
}

function render() {
  if (!state) return;
  drawBoard();
  drawOverlay();
  updateSidebar();
  if (state.winner) showWin(state.winner);
}

function updateSidebar() {
  if (!state) return;
  const wr = state.walls_remaining;

  // Wall counts
  document.getElementById('walls-x').textContent = wr.x;
  document.getElementById('walls-o').textContent = wr.o;

  // Wall pips (10 max)
  renderPips('pips-x', wr.x, 'pip-x');
  renderPips('pips-o', wr.o, 'pip-o');

  // Active card highlight
  document.getElementById('card-x').classList.toggle('active-turn', state.current_player === 'x');
  document.getElementById('card-o').classList.toggle('active-turn', state.current_player === 'o');

  // Mode buttons: disable during AI turn or when game over
  const canAct = state.current_player === 'x' && !state.winner;
  ['btn-pawn', 'btn-wall-h', 'btn-wall-v'].forEach(id => {
    document.getElementById(id).disabled = !canAct;
  });
  if (!canAct && mode !== 'pawn') setMode('pawn');

  // Disable wall modes if no walls left
  if (wr.x === 0) {
    document.getElementById('btn-wall-h').disabled = true;
    document.getElementById('btn-wall-v').disabled = true;
  }
}

function renderPips(id, count, cls) {
  const el = document.getElementById(id);
  el.innerHTML = '';
  for (let i = 0; i < 10; i++) {
    const pip = document.createElement('div');
    pip.className = 'pip ' + (i < count ? cls : 'used');
    el.appendChild(pip);
  }
}

function setTurnBar(text, color) {
  const bar = document.getElementById('turn-bar');
  bar.textContent = text;
  bar.style.color = color || '';
}

function setThinking(v) {
  document.getElementById('thinking-bar').classList.toggle('visible', v);
}

function flashHint(msg) {
  const el = document.getElementById('hint-text');
  el.textContent = msg;
  el.style.color = '#e05c3a';
  setTimeout(() => {
    el.textContent = '';
    el.style.color = '';
  }, 2000);
}

function addLog(msg, cls) {
  const el = document.createElement('div');
  el.className = `log-entry ${cls}`;
  el.textContent = `#${String(moveCount).padStart(2, '0')} ${msg}`;
  const log = document.getElementById('log-entries');
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
}

function showWin(winner) {
  const overlay = document.getElementById('win-overlay');
  const title   = document.getElementById('win-title');
  const sub     = document.getElementById('win-sub');
  if (winner === 'x') {
    title.textContent = 'YOU WIN';
    title.className   = 'win-title';
    sub.textContent   = 'Congratulations — you outplayed the machine.';
  } else {
    title.textContent = 'CPU WINS';
    title.className   = 'win-title cpu-win';
    sub.textContent   = 'Better luck next time. The MCTS never sleeps.';
  }
  overlay.classList.add('visible');
  setTurnBar('GAME OVER');
}

// ── Init ──────────────────────────────────────────────────────
(async () => {
  // Try to load existing state, else start fresh
  try {
    const res = await fetch(`${API}/state`);
    if (res.ok) {
      state = await res.json();
      if (state.current_player === 'x' && !state.winner) await fetchLegal();
      render();
      setTurnBar(state.current_player === 'x' ? 'YOUR TURN' : 'CPU TURN');
    } else {
      await newGame();
    }
  } catch {
    // Server not up yet — draw an empty board
    drawBoard();
    setTurnBar('CONNECTING TO SERVER…');
    setTimeout(async () => {
      try { await newGame(); } catch {}
    }, 1500);
  }
})();
