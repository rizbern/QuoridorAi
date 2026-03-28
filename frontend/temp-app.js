// ─────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────

const API   = "http://localhost:8000";
const HUMAN = 1;
const AI    = 2;

let gameState   = null;
let busy        = false;
let selected    = false;
let validMoves  = [];

// Drag-and-drop wall state
let dragging    = false;   // currently dragging a wall
let dragOri     = null;    // "H" | "V"
let dragRow     = null;
let dragCol     = null;

// ─────────────────────────────────────────────
// Build 17×17 visual grid
// ─────────────────────────────────────────────

function createBoard() {
  const boardEl = document.getElementById("board");
  boardEl.innerHTML = "";

  for (let vRow = 0; vRow < 17; vRow++) {
    for (let vCol = 0; vCol < 17; vCol++) {
      const div     = document.createElement("div");
      const evenRow = vRow % 2 === 0;
      const evenCol = vCol % 2 === 0;

      if (evenRow && evenCol) {
        const gRow = vRow / 2;
        const gCol = vCol / 2;
        div.classList.add("cell");
        div.dataset.row = gRow;
        div.dataset.col = gCol;

      } else if (!evenRow && evenCol) {
        // Horizontal wall slot (between rows)
        const wRow = (vRow - 1) / 2;
        const wCol = vCol / 2;
        div.classList.add("h-wall-slot");
        div.dataset.wallRow = wRow;
        div.dataset.wallCol = wCol;
        div.dataset.wallOri = "H";

      } else if (evenRow && !evenCol) {
        // Vertical wall slot (between cols)
        const wRow = vRow / 2;
        const wCol = (vCol - 1) / 2;
        div.classList.add("v-wall-slot");
        div.dataset.wallRow = wRow;
        div.dataset.wallCol = wCol;
        div.dataset.wallOri = "V";

      } else {
        div.classList.add("wall-intersection");
      }

      boardEl.appendChild(div);
    }
  }

  // Single delegated listener for clicks (pawn moves)
  boardEl.addEventListener("click",      onBoardClick);

  // Drag-and-drop for walls
  boardEl.addEventListener("mousedown",  onBoardMouseDown);
  boardEl.addEventListener("mouseover",  onBoardMouseOver);
  boardEl.addEventListener("mouseup",    onBoardMouseUp);

  // Cancel drag if mouse leaves board
  boardEl.addEventListener("mouseleave", () => cancelDrag());

  // Prevent default drag behavior on wall slots
  boardEl.addEventListener("dragstart", e => e.preventDefault());
}

// ─────────────────────────────────────────────
// Click handler — pawn selection & movement
// ─────────────────────────────────────────────

function onBoardClick(e) {
  if (busy || !gameState || gameState.is_terminal) return;
  if (Number(gameState.current_player) !== HUMAN) return;
  if (dragging) return; // ignore clicks that were actually drag-ends

  const cell = e.target.closest(".cell");
  if (!cell) return;

  const row = Number(cell.dataset.row);
  const col = Number(cell.dataset.col);

  const humanPawn = gameState.pawns[HUMAN] || gameState.pawns["1"];
  const pawnRow   = Number(humanPawn[0]);
  const pawnCol   = Number(humanPawn[1]);

  if (!selected) {
    // Click own pawn → select it
    if (row === pawnRow && col === pawnCol) {
      selected = true;
      cell.classList.add("selected-pawn");
      showValidMoves();
    }
    return;
  }

  // Already selected
  if (row === pawnRow && col === pawnCol) {
    // Click own pawn again → deselect
    deselect();
    return;
  }

  const isValid = validMoves.some(([r, c]) => r === row && c === col);
  if (isValid) {
    deselect();
    sendPawnMove(row, col);
  } else {
    deselect();
    // Try selecting pawn again if clicked on it
    if (row === pawnRow && col === pawnCol) {
      selected = true;
      cell.classList.add("selected-pawn");
      showValidMoves();
    }
  }
}

// ─────────────────────────────────────────────
// Drag-and-drop wall handlers
// ─────────────────────────────────────────────

function onBoardMouseDown(e) {
  if (busy || !gameState || gameState.is_terminal) return;
  if (Number(gameState.current_player) !== HUMAN) return;
  if (e.button !== 0) return;

  const wallEl = e.target.closest(".h-wall-slot, .v-wall-slot");
  if (!wallEl) return;

  const ori = wallEl.dataset.wallOri;
  const row = Number(wallEl.dataset.wallRow);
  const col = Number(wallEl.dataset.wallCol);

  // Only start drag on non-placed slots
  if (wallEl.classList.contains("placed")) return;

  dragging = true;
  dragOri  = ori;
  dragRow  = row;
  dragCol  = col;

  // Preview immediately
  clearWallPreviews();
  highlightWallPreview(row, col, ori);

  e.preventDefault(); // stop text selection
}

function onBoardMouseOver(e) {
  if (!dragging) return;

  const wallEl = e.target.closest(`.${dragOri === "H" ? "h" : "v"}-wall-slot`);
  if (!wallEl) return;

  const row = Number(wallEl.dataset.wallRow);
  const col = Number(wallEl.dataset.wallCol);

  if (row === dragRow && col === dragCol) return;

  dragRow = row;
  dragCol = col;

  clearWallPreviews();
  highlightWallPreview(row, col, dragOri);
}

function onBoardMouseUp(e) {
  if (!dragging) return;

  const wasRow = dragRow;
  const wasCol = dragCol;
  const wasOri = dragOri;

  cancelDrag();
  clearWallPreviews();

  if (busy || !gameState || gameState.is_terminal) return;
  if (Number(gameState.current_player) !== HUMAN) return;

  sendWallMove(wasRow, wasCol, wasOri);
}

function cancelDrag() {
  if (!dragging) return;
  dragging = false;
  dragOri  = null;
  dragRow  = null;
  dragCol  = null;
  clearWallPreviews();
}

// ─────────────────────────────────────────────
// Wall preview
// ─────────────────────────────────────────────

function highlightWallPreview(row, col, orientation) {
  const s1 = getWallSlot(row, col, orientation);
  if (s1 && !s1.classList.contains("placed")) s1.classList.add("preview");

  if (orientation === "H" && col + 1 <= 7) {
    const s2 = getWallSlot(row, col + 1, "H");
    if (s2 && !s2.classList.contains("placed")) s2.classList.add("preview-adj");
  } else if (orientation === "V" && row + 1 <= 7) {
    const s2 = getWallSlot(row + 1, col, "V");
    if (s2 && !s2.classList.contains("placed")) s2.classList.add("preview-adj");
  }
}

function clearWallPreviews() {
  document.querySelectorAll(".preview, .preview-adj")
    .forEach(el => el.classList.remove("preview", "preview-adj"));
}

// ─────────────────────────────────────────────
// Selection helpers
// ─────────────────────────────────────────────

function deselect() {
  selected = false;
  document.querySelectorAll(".selected-pawn").forEach(c => c.classList.remove("selected-pawn"));
  clearValidMoves();
}

function showValidMoves() {
  clearValidMoves();
  if (!gameState) return;
  fetch(`${API}/legal-moves/${HUMAN}`)
    .then(r => r.json())
    .then(data => {
      validMoves = data.moves
        .filter(m => m.type === "move")
        .map(m => [m.data[0], m.data[1]]);
      validMoves.forEach(([r, c]) => {
        const cell = getCell(r, c);
        if (cell) cell.classList.add("valid-move");
      });
    })
    .catch(err => console.error("showValidMoves:", err));
}

function clearValidMoves() {
  validMoves = [];
  document.querySelectorAll(".cell.valid-move").forEach(c => c.classList.remove("valid-move"));
}

// ─────────────────────────────────────────────
// Wall counters
// ─────────────────────────────────────────────

function buildCounters() {
  buildCounterGroup("p2-counter", 10);
  buildCounterGroup("p1-counter", 10);
}

function buildCounterGroup(id, total) {
  const el = document.getElementById(id);
  el.innerHTML = "";
  for (let i = 0; i < total; i++) {
    const bar = document.createElement("div");
    bar.classList.add("wall-bar");
    el.appendChild(bar);
  }
}

function updateCounters(state) {
  const w  = state.remaining_walls;
  const p1 = Number(w[1] !== undefined ? w[1] : w["1"]);
  const p2 = Number(w[2] !== undefined ? w[2] : w["2"]);
  updateCounterGroup("p1-counter", isNaN(p1) ? 10 : p1);
  updateCounterGroup("p2-counter", isNaN(p2) ? 10 : p2);
}

function updateCounterGroup(id, remaining) {
  document.querySelectorAll(`#${id} .wall-bar`).forEach((bar, i) => {
    bar.classList.toggle("used", i >= remaining);
  });
}

// ─────────────────────────────────────────────
// API calls
// ─────────────────────────────────────────────

async function sendPawnMove(row, col) {
  setBusy(true);
  try {
    const res  = await fetch(`${API}/move/pawn`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ player: HUMAN, position: [row, col] })
    });
    const data = await res.json();
    if (!res.ok) {
      console.error("Pawn move rejected:", data);
      setStatus(data.detail || "Invalid move — try again");
      setBusy(false);
      return;
    }
    applyState(data);
  } catch (err) {
    console.error("sendPawnMove:", err);
    setStatus("Cannot reach server");
    setBusy(false);
  }
}

async function sendWallMove(row, col, orientation) {
  setBusy(true);
  try {
    const res  = await fetch(`${API}/move/wall`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ player: HUMAN, row, col, orientation })
    });
    const data = await res.json();
    if (!res.ok) {
      console.error("Wall rejected:", data);
      setStatus(data.detail || "Invalid wall — try again");
      setBusy(false);
      return;
    }
    applyState(data);
  } catch (err) {
    console.error("sendWallMove:", err);
    setStatus("Cannot reach server");
    setBusy(false);
  }
}

async function resetGame() {
  setBusy(false);
  deselect();
  cancelDrag();
  try {
    const res  = await fetch(`${API}/reset`, { method: "POST" });
    const data = await res.json();
    document.getElementById("overlay").classList.remove("show");
    applyState(data);
  } catch (err) {
    console.error("resetGame:", err);
    setStatus("Cannot reach server");
  }
}

async function loadState() {
  try {
    const res  = await fetch(`${API}/state`);
    const data = await res.json();
    console.log("Initial state:", data);
    applyState(data);
  } catch (err) {
    console.error("loadState:", err);
    setStatus("Start the server: python run.py");
  }
}

// ─────────────────────────────────────────────
// Apply state → DOM  (the key fix: always re-render)
// ─────────────────────────────────────────────

function applyState(state) {
  gameState = state;
  console.log("State — player:", state.current_player, "winner:", state.winner);

  // Always re-render pawns and walls immediately
  renderPawns(state.pawns);
  renderWalls(state.walls);
  updateCounters(state);
  clearWallPreviews();
  deselect();
  updateStatus(state);

  if (state.is_terminal) {
    showWinner(state.winner);
  }

  setBusy(false);
}

// ─────────────────────────────────────────────
// Render pawns — moves token to new cell instantly
// ─────────────────────────────────────────────

function renderPawns(pawns) {
  // Remove all existing pawn tokens
  document.querySelectorAll(".pawn-token").forEach(p => p.remove());

  Object.entries(pawns).forEach(([player, pos]) => {
    const row  = Number(pos[0]);
    const col  = Number(pos[1]);
    const cell = getCell(row, col);
    if (!cell) {
      console.warn("Cell not found for pawn", player, pos);
      return;
    }
    const token = document.createElement("div");
    token.classList.add("pawn-token", `p${player}`);
    token.style.pointerEvents = "none"; // clicks fall through to cell
    cell.appendChild(token);
  });
}

// ─────────────────────────────────────────────
// Render walls
// ─────────────────────────────────────────────

function renderWalls(walls) {
  document.querySelectorAll(".placed").forEach(el => el.classList.remove("placed"));
  walls.forEach(w => {
    const row = Number(w[0]);
    const col = Number(w[1]);
    const ori = w[2];
    const s1  = getWallSlot(row, col, ori);
    if (s1) s1.classList.add("placed");
    const s2  = ori === "H"
      ? getWallSlot(row, col + 1, ori)
      : getWallSlot(row + 1, col, ori);
    if (s2) s2.classList.add("placed");
  });
}

// ─────────────────────────────────────────────
// Status bar
// ─────────────────────────────────────────────

function updateStatus(state) {
  if (state.is_terminal) {
    setStatus(Number(state.winner) === HUMAN ? "You win! 🎉" : "AI wins — good game.");
    return;
  }
  if (Number(state.current_player) === HUMAN) {
    setStatus("Your turn — click your pawn, or drag a wall onto the board");
  } else {
    setStatus("AI is thinking…", true);
  }
}

function setStatus(text, thinking = false) {
  const el = document.getElementById("status-bar");
  el.textContent = text;
  el.classList.toggle("thinking", thinking);
}

// ─────────────────────────────────────────────
// Winner overlay
// ─────────────────────────────────────────────

function showWinner(winner) {
  document.getElementById("overlay-icon").textContent  = Number(winner) === HUMAN ? "○" : "●";
  document.getElementById("overlay-title").textContent = Number(winner) === HUMAN ? "You Win!" : "AI Wins";
  document.getElementById("overlay-sub").textContent   =
    Number(winner) === HUMAN ? "Well played!" : "Better luck next time.";
  document.getElementById("overlay").classList.add("show");
}

// ─────────────────────────────────────────────
// Busy lock
// ─────────────────────────────────────────────

function setBusy(val) {
  busy = val;
  document.getElementById("board").style.pointerEvents = val ? "none" : "all";
}

// ─────────────────────────────────────────────
// DOM helpers
// ─────────────────────────────────────────────

function getCell(row, col) {
  return document.querySelector(`.cell[data-row="${row}"][data-col="${col}"]`);
}

function getWallSlot(row, col, orientation) {
  const cls = orientation === "H" ? ".h-wall-slot" : ".v-wall-slot";
  return document.querySelector(`${cls}[data-wall-row="${row}"][data-wall-col="${col}"]`);
}

// ─────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────

createBoard();
buildCounters();
loadState();