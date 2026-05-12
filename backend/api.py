# -*- coding: utf-8 -*-
"""
api.py — FastAPI backend for Quoridor.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Tuple
import sys, os

sys.path.insert(0, os.path.dirname(__file__))

from board import (
    initGame, findPawn, getLegalPawnMoves,
    movePawn, placeWall, BOARD_SIZE, isValidWallPlacement
)
from ai import get_ai_move

app = FastAPI(title="Quoridor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory game state ──────────────────────────────────────
_state: dict = initGame()
_last_ai_pos: Optional[Tuple[int, int]] = None


def _serialize(state: dict) -> dict:
    board = state["board"]
    walls = []
    pawns = {}
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            if cell == "x":
                pawns["x"] = {"board_row": r, "board_col": c}
            elif cell == "o":
                pawns["o"] = {"board_row": r, "board_col": c}
            elif cell in ("-", "|"):
                walls.append({"board_row": r, "board_col": c, "type": cell})
    return {
        "board": [row[:] for row in board],
        "pawns": pawns,
        "walls": walls,
        "walls_remaining": state["walls_remaining"],
        "current_player": state["current_player"],
        "winner": state["winner"],
    }


class PawnMove(BaseModel):
    display_row: int
    display_col: int


class WallMove(BaseModel):
    board_row: int
    board_col: int
    orientation: str   # 'H' or 'V'


@app.get("/state")
def get_state():
    return _serialize(_state)


@app.post("/new-game")
def new_game():
    global _state, _last_ai_pos
    _state = initGame()
    _last_ai_pos = None
    return _serialize(_state)


@app.get("/legal-moves")
def legal_moves():
    moves = getLegalPawnMoves(_state["board"], "x")
    return {
        "moves": [{"board_row": r, "board_col": c} for r, c in moves]
    }


@app.post("/move/pawn")
def human_pawn(req: PawnMove):
    global _state
    if _state["current_player"] != "x":
        raise HTTPException(400, "Not your turn")
    if _state["winner"]:
        raise HTTPException(400, "Game over")
    br, bc = req.display_row * 2, req.display_col * 2
    new = movePawn(_state, "x", br, bc)
    if new is None:
        raise HTTPException(400, "Illegal move")
    _state = new
    return _serialize(_state)


@app.post("/move/wall")
def human_wall(req: WallMove):
    global _state
    if _state["current_player"] != "x":
        raise HTTPException(400, "Not your turn")
    if _state["winner"]:
        raise HTTPException(400, "Game over")
    if req.orientation not in ("H", "V"):
        raise HTTPException(400, "Bad orientation")
    new = placeWall(_state, "x", (req.board_row, req.board_col), req.orientation)
    if new is None:
        raise HTTPException(400, "Invalid wall")
    _state = new
    return _serialize(_state)


@app.post("/move/ai")
def ai_turn():
    global _state, _last_ai_pos
    if _state["current_player"] != "o":
        raise HTTPException(400, "Not AI's turn")
    if _state["winner"]:
        raise HTTPException(400, "Game over")
    prev = findPawn(_state["board"], "o")
    move = get_ai_move(_state, last_ai_pos=_last_ai_pos)
    if move is None:
        raise HTTPException(500, "AI stuck")
    if move["type"] == "pawn":
        r, c = move["target"]
        new = movePawn(_state, "o", r, c)
        if new is None:
            raise HTTPException(500, "AI move invalid")
        _last_ai_pos = prev
        _state = new
        return {**_serialize(_state), "ai_move": {"type": "pawn", "board_row": r, "board_col": c}}
    else:
        ar, ac = move["anchor"]
        ori = move["orientation"]
        new = placeWall(_state, "o", (ar, ac), ori)
        if new is None:
            raise HTTPException(500, "AI wall invalid")
        _last_ai_pos = None
        _state = new
        return {**_serialize(_state), "ai_move": {"type": "wall", "board_row": ar, "board_col": ac, "orientation": ori}}


@app.get("/validate-wall")
def validate_wall(board_row: int, board_col: int, orientation: str):
    valid, reason = isValidWallPlacement(
        _state["board"], _state["walls_remaining"],
        "x", (board_row, board_col), orientation
    )
    return {"valid": valid, "reason": reason}
