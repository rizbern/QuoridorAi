const boardDiv = document.getElementById("board");

function createBoard() {
  for (let row = 0; row < 17; row++) {
    for (let col = 0; col < 17; col++) {

      const div = document.createElement("div");

      if (row % 2 === 0 && col % 2 === 0) {
        div.classList.add("cell");
      } else if (row % 2 === 1 && col % 2 === 0) {
        div.classList.add("horizontal-wall");
      } else if (row % 2 === 0 && col % 2 === 1) {
        div.classList.add("vertical-wall");
      } else {
        div.classList.add("wall-intersection");
      }

      board.appendChild(div);
    }
  }
}

async function playerMove(x, y) {
  const response = await fetch("/move", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ position: [x, y] })
  });

  const data = await response.json();
  updateBoard(data.state);
}

function updateBoard(state) {
  document.querySelectorAll(".cell").forEach(c => c.textContent = "");

  state.pawns && Object.entries(state.pawns).forEach(([p, pos]) => { // p = player move, pos = [x, y]
    const cell = document.querySelector(`[data-x="${pos[0]}"][data-y="${pos[1]}"]`);
    cell.textContent = p;
  });
}

createBoard();