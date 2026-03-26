# backend/api 
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from board import Board

app = FastAPI()

# Runs everytime requests are made -> middleman
# Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

board = Board()

# Player moves section

class PawnMoveRequest(BaseModel):
    player: int          # 1 or 2
    position: list[int]  # [row, col] format

# { "player": 1, "row": 3, "col": 4, "orientation": "H" }
class WallMoveRequest(BaseModel):
    player: int          # 1 or 2
    row: int
    col: int
    orientation: str     # "H" or "V"

# defined in board.py
def serialize_board(b: Board) -> dict:
    # Convert to json
    return {
        "pawns": {str(k): list(v) for k, v in b.pawns.items()},
        # Each wall is (row, col, orientation) — convert tuple to list
        "walls": [list(w) for w in b.walls],
        "remaining_walls": b.remaining_walls,
        "current_player": b.current_player,
        "winner": b.get_winner(),
        "is_terminal": b.is_terminal(),
    }

def check_turn(player: int):
    """Raises 400 if it's not this player's turn."""
    if board.current_player != player:
        raise HTTPException(
            status_code=400,
            detail=f"It is player {board.current_player}'s turn, not player {player}'s."
        )

# Endpoints

@app.get("/")
def root():
    return {"message": "Quoridor API running"}

@app.get("/state")
def get_state():
    # Returns the current board state.
    return serialize_board(board)

@app.post("/move/pawn")
def pawn_move(req: PawnMoveRequest):
    # Move a pawn to a new position.
    # Body: { "player": 1, "position": [row, col] }
    if board.is_terminal():
        return serialize_board(board)

    check_turn(req.player)

    position = tuple(req.position)
    success = board.move_pawn(req.player, position)

    # Checks if move is valid
    if not success:
        raise HTTPException(status_code=400, detail="Invalid pawn move.")

    return serialize_board(board)

@app.post("/move/wall")
def wall_move(req: WallMoveRequest):
    # Place a wall on the board.
    # Body: { "player": 1, "row": 3, "col": 4, "orientation": "H" }

    if board.is_terminal():
        return serialize_board(board)

    check_turn(req.player)

    if req.orientation not in ("H", "V"):
        raise HTTPException(status_code=400, detail="Orientation must be 'H' or 'V'.")

    success = board.place_wall(req.player, req.row, req.col, req.orientation)

    # Checks if move is valid
    if not success:
        raise HTTPException(status_code=400, detail="Invalid wall placement.")

    return serialize_board(board)

@app.get("/legal-moves/{player}")
def legal_moves(player: int):

    # Returns all legal moves for a player.
    # Useful for highlighting valid moves in the frontend.
    
    if player not in (1, 2):
        raise HTTPException(status_code=400, detail="Player must be 1 or 2.")

    moves = board.get_legal_moves(player)

    # Serialize move tuples into JSON lists
    serialized = []
    for move_type, data in moves:
        serialized.append({
            "type": move_type, # either a move or a wall plac
            "data": list(data) # postion
        })

    return {"moves": serialized}

@app.post("/reset")
def reset_game():
    # resets the board to a fresh game.
    global board
    board = Board()
    return serialize_board(board)