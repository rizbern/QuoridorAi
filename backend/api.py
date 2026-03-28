from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from board import Board
from mcts import MCTS

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

board  = Board()
ai     = MCTS(simulations=1000)   # AI plays as player 2


# ─────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────

class PawnMoveRequest(BaseModel):
    player: int
    position: list[int]   # [row, col]

class WallMoveRequest(BaseModel):
    player: int
    row: int
    col: int
    orientation: str      # "H" or "V"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def serialize_board(b: Board) -> dict:
    return {
        "pawns":           {str(k): list(v) for k, v in b.pawns.items()},
        "walls":           [list(w) for w in b.walls],
        "remaining_walls": b.remaining_walls,
        "current_player":  b.current_player,
        "winner":          b.get_winner(),
        "is_terminal":     b.is_terminal(),
    }

def check_turn(player: int):
    if board.current_player != player:
        raise HTTPException(
            status_code=400,
            detail=f"It is player {board.current_player}'s turn, not player {player}'s."
        )


# ─────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "Quoridor API running"}


@app.get("/state")
def get_state():
    return serialize_board(board)


@app.post("/move/pawn")
def pawn_move(req: PawnMoveRequest):
    """Human player moves their pawn. AI responds automatically."""
    if board.is_terminal():
        return serialize_board(board)

    check_turn(req.player)

    # --- Human move ---
    success = board.move_pawn(req.player, tuple(req.position))
    if not success:
        raise HTTPException(status_code=400, detail="Invalid pawn move.")

    # --- AI responds immediately if game is still running ---
    if not board.is_terminal():
        ai_move = ai.get_best_move(board)
        board.apply_move(2, ai_move)

    return serialize_board(board)


@app.post("/move/wall")
def wall_move(req: WallMoveRequest):
    """Human player places a wall. AI responds automatically."""
    if board.is_terminal():
        return serialize_board(board)

    check_turn(req.player)

    if req.orientation not in ("H", "V"):
        raise HTTPException(status_code=400, detail="Orientation must be 'H' or 'V'.")

    success = board.place_wall(req.player, req.row, req.col, req.orientation)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid wall placement.")

    # --- AI responds immediately if game is still running ---
    if not board.is_terminal():
        ai_move = ai.get_best_move(board)
        board.apply_move(2, ai_move)

    return serialize_board(board)


@app.get("/legal-moves/{player}")
def legal_moves(player: int):
    if player not in (1, 2):
        raise HTTPException(status_code=400, detail="Player must be 1 or 2.")

    moves = board.get_legal_moves(player)
    serialized = [{"type": t, "data": list(d)} for t, d in moves]
    return {"moves": serialized}


@app.post("/reset")
def reset_game():
    global board
    board = Board()
    return serialize_board(board)