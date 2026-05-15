from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from board import (
    initGame, findPawn, getLegalPawnMoves,
    movePawn, placeWall, BOARD_SIZE, isValidWallPlacement
)
from ai import get_ai_move

app = Flask(__name__)
CORS(app)

FRONTEND = os.path.join(os.path.dirname(__file__), '..', 'frontend')

_state       = initGame()
_last_ai_pos = None


def _serialize(state):
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
        "board":           [row[:] for row in board],
        "pawns":           pawns,
        "walls":           walls,
        "walls_remaining": state["walls_remaining"],
        "current_player":  state["current_player"],
        "winner":          state["winner"],
    }


@app.route("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND, filename)


@app.route("/state", methods=["GET"])
def get_state():
    return jsonify(_serialize(_state))


@app.route("/new-game", methods=["POST"])
def new_game():
    global _state, _last_ai_pos
    _state       = initGame()
    _last_ai_pos = None
    return jsonify(_serialize(_state))


@app.route("/legal-moves", methods=["GET"])
def legal_moves():
    moves = getLegalPawnMoves(_state["board"], "x")
    return jsonify({
        "moves": [{"board_row": r, "board_col": c} for r, c in moves]
    })


@app.route("/move/pawn", methods=["POST"])
def human_pawn():
    global _state
    data = request.get_json()
    if _state["current_player"] != "x":
        return jsonify({"error": "Not your turn"}), 400
    if _state["winner"]:
        return jsonify({"error": "Game over"}), 400
    br  = data.get("display_row", 0) * 2
    bc  = data.get("display_col", 0) * 2
    new = movePawn(_state, "x", br, bc)
    if new is None:
        return jsonify({"error": "Illegal move"}), 400
    _state = new
    return jsonify(_serialize(_state))


@app.route("/move/wall", methods=["POST"])
def human_wall():
    global _state
    data = request.get_json()
    if _state["current_player"] != "x":
        return jsonify({"error": "Not your turn"}), 400
    if _state["winner"]:
        return jsonify({"error": "Game over"}), 400
    ori = data.get("orientation", "")
    if ori not in ("H", "V"):
        return jsonify({"error": "Bad orientation"}), 400
    anchor = (data.get("board_row", 0), data.get("board_col", 0))
    new    = placeWall(_state, "x", anchor, ori)
    if new is None:
        return jsonify({"error": "Invalid wall"}), 400
    _state = new
    return jsonify(_serialize(_state))


@app.route("/move/ai", methods=["POST"])
def ai_turn():
    global _state, _last_ai_pos
    if _state["current_player"] != "o":
        return jsonify({"error": "Not AI's turn"}), 400
    if _state["winner"]:
        return jsonify({"error": "Game over"}), 400
    prev = findPawn(_state["board"], "o")
    move = get_ai_move(_state, last_ai_pos=_last_ai_pos)
    if move is None:
        return jsonify({"error": "AI stuck"}), 500
    if move["type"] == "pawn":
        r, c = move["target"]
        new  = movePawn(_state, "o", r, c)
        if new is None:
            return jsonify({"error": "AI move invalid"}), 500
        _last_ai_pos = prev
        _state       = new
        return jsonify({
            **_serialize(_state),
            "ai_move": {"type": "pawn", "board_row": r, "board_col": c}
        })
    else:
        ar, ac = move["anchor"]
        ori    = move["orientation"]
        new    = placeWall(_state, "o", (ar, ac), ori)
        if new is None:
            return jsonify({"error": "AI wall invalid"}), 500
        _last_ai_pos = None
        _state       = new
        return jsonify({
            **_serialize(_state),
            "ai_move": {"type": "wall", "board_row": ar, "board_col": ac, "orientation": ori}
        })


@app.route("/validate-wall", methods=["GET"])
def validate_wall():
    board_row   = int(request.args.get("board_row", 0))
    board_col   = int(request.args.get("board_col", 0))
    orientation = request.args.get("orientation", "")
    valid, reason = isValidWallPlacement(
        _state["board"], _state["walls_remaining"],
        "x", (board_row, board_col), orientation
    )
    return jsonify({"valid": valid, "reason": reason})