# -*- coding: utf-8 -*-
"""
game.py — Terminal game loop for Quoridor.

This file is the bridge between the board engine (board.py),
the AI (ai.py), and the player. When you build a frontend,
this file is your reference for:

  - How game state flows turn by turn
  - How human moves are validated and applied
  - How AI moves are requested and applied
  - How the board is rendered (the 17x17 internal grid → 9x9 display)
  - How walls are converted between display coords and board coords

STATE DICT (passed everywhere):
  state = {
    'board':            17x17 list of lists
                        '.' = empty cell
                        'x' = human pawn
                        'o' = AI pawn
                        '-' = horizontal wall segment
                        '|' = vertical wall segment

    'walls_remaining':  {'x': int, 'o': int}  — walls each player has left (max 10)

    'current_player':   'x' (human) or 'o' (AI) — whose turn it is

    'winner':           None | 'x' | 'o'  — set when game ends
  }

COORDINATE SYSTEMS:
  Display coords:  0-8  (what the player sees)
  Board coords:    0-16 (internal 17x17 grid)
  Conversion:      board_row = display_row * 2
                   board_col = display_col * 2

  Wall anchors in board coords:
    H wall: (odd_row, even_col)  — sits between pawn rows
    V wall: (even_row, odd_col)  — sits between pawn cols
"""

import sys

from board import (
    initGame,       # creates a fresh game state dict
    findPawn,       # returns (board_row, board_col) of a player's pawn
    getLegalPawnMoves,  # returns list of valid (board_row, board_col) targets
    movePawn,       # applies a pawn move, returns new state or None if illegal
    placeWall,      # applies a wall, returns new state or None if illegal
    checkWin,       # returns True if player has reached their goal row
    BOARD_SIZE      # 17
)
from ai import get_ai_move  # returns {'type': 'pawn'/'wall', ...} for AI's best move


# ─────────────────────────────────────────────────────────────
# RENDERING
# Converts the 17x17 internal board into a readable terminal display.
# Frontend equivalent: this is your drawBoard() function.
# ─────────────────────────────────────────────────────────────

def render(state, highlights=None):
    """
    Print the current board state to the terminal.

    Appearance matches the reference style:
      - Column labels A-I across the top
      - Row labels 1-9 down the left side
      - '+' at every intersection point
      - '.' for empty cells
      - 'W' for human pawn (white), 'B' for AI pawn (black)
      - '*' for highlighted valid moves
      - '---' for horizontal walls, '|' for vertical walls
      - Dashed border top and bottom

    Args:
        state:      the game state dict
        highlights: list of board coords [(board_row, board_col), ...]
                    to mark as valid move targets ('*')
                    NOTE: these are BOARD coords (0-16), not display coords (0-8)

    Frontend notes:
        - Board cells are at even row + even col in the 17x17 grid
        - Horizontal walls are at odd row + even col (spans 3 cells wide)
        - Vertical walls are at even row + odd col (spans 3 cells tall)
        - Wall intersections are at odd row + odd col (purely visual)
    """
    board      = state['board']
    wr         = state['walls_remaining']
    cp         = state['current_player']
    highlights = highlights or []

    # ── Header ───────────────────────────────────────────────
    print()
    print(f"  Walls — W: {wr['x']}  |  B: {wr['o']}      "
          f"Turn: {'YOU (W)' if cp == 'x' else 'CPU (B)'}")
    print()

    # Column labels: A through I, spaced to align with cells
    # Each cell takes 4 chars wide (e.g. " . +"), last cell takes 3
    col_labels = "   " + "  ".join(f"  {chr(65+i)} " for i in range(9))
    print(col_labels)

    # Top border: +---+---+---+ ...
    top_border = "   +" + "+".join(["---"] * 9) + "+"
    print(top_border)

    # ── Board rows ───────────────────────────────────────────
    for row in range(BOARD_SIZE):

        if row % 2 == 0:
            # ── Pawn row (display rows 1-9) ──────────────────
            # Format: row_label | cell + cell + ... cell |
            # Left edge is always '|', right edge is always '|'
            # Between cells: '|' if vertical wall, '+' otherwise

            display_row = row // 2 + 1   # display rows are 1-indexed
            line = f"{display_row:2d} |"

            for col in range(BOARD_SIZE):
                cell = board[row][col]

                if col % 2 == 0:
                    # Playable cell — show pawn, highlight, or dot
                    br = row          # board row (for highlight lookup)
                    bc = col          # board col (for highlight lookup)

                    if (br, bc) in highlights:
                        line += " * "   # valid move destination
                    elif cell == 'x':
                        line += " W "   # human pawn (White)
                    elif cell == 'o':
                        line += " B "   # AI pawn (Black)
                    else:
                        line += " . "   # empty cell

                else:
                    # Vertical wall slot — '|' if wall, '+' if open
                    if cell == '|':
                        line += "|"     # vertical wall segment
                    else:
                        line += "+"     # open passage intersection

            line += "|"   # right border
            print(line)

        else:
            # ── Wall row (between pawn rows) ──────────────────
            # Format: "   +" + cell segments separated by '+'
            # Each cell: "---" if H wall, "   " if open, "+++" at corners
            # Intersections: '+' always (wall or not)

            line = "   +"

            for col in range(BOARD_SIZE):
                cell = board[row][col]

                if col % 2 == 0:
                    # Horizontal wall cell or open gap
                    if cell == '-':
                        line += "---"   # horizontal wall segment
                    else:
                        line += "   "   # open gap (no wall)

                else:
                    # Intersection point between 4 cells — always '+'
                    line += "+"

            print(line)

    # Bottom border
    print(top_border)
    print()


# ─────────────────────────────────────────────────────────────
# INPUT HELPERS
# Small utilities for parsing terminal input.
# Frontend equivalent: you won't need these — replace with
# click/drag events from the UI.
# ─────────────────────────────────────────────────────────────

def prompt(msg):
    """Read a line from stdin, strip whitespace, lowercase it."""
    return input(msg).strip().lower()


def parse_coord(s):
    """
    Parse a coordinate string like '4 4' or '4,4' into (int, int).
    Returns None if the input is malformed.

    Frontend equivalent: you get row/col directly from a click event,
    so this function isn't needed in the frontend.
    """
    try:
        parts = s.replace(',', ' ').split()
        if len(parts) != 2:
            return None
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        return None


def board_to_grid(gr, gc):
    """
    Convert display coordinates (0-8) to board array coordinates (0-16).

    The internal board is 17x17. Pawn cells live at even indices only.
    So display row 3 = board row 6, display col 4 = board col 8.

    Frontend: call this whenever the player clicks a cell to get
    the board coords needed by movePawn().

    Example:
        display (4, 4) → board (8, 8)  — the center cell
        display (0, 4) → board (0, 8)  — human start
        display (8, 4) → board (16, 8) — AI start
    """
    return gr * 2, gc * 2


# ─────────────────────────────────────────────────────────────
# HUMAN TURN HANDLING
# These functions manage the human player's input loop.
#
# Frontend equivalent:
#   human_turn()   → your onClick / onDrop event handlers
#   do_pawn_move() → your handlePawnClick() function
#   do_wall_move() → your handleWallDrop() function
#
# The key API calls for the frontend are:
#   getLegalPawnMoves(board, 'x')          → highlight valid cells
#   movePawn(state, 'x', board_row, col)   → apply pawn move
#   placeWall(state, 'x', anchor, ori)     → apply wall placement
# ─────────────────────────────────────────────────────────────

def human_turn(state):
    """
    Handle one full human turn — loops until a valid move is made.

    Returns the new game state after the human's move.

    Frontend equivalent:
        This loop doesn't exist in a frontend — instead you just
        wait for the player to click/drag, validate, and apply.
        The function returns the new state which you use to re-render.
    """
    while True:
        print("Your move:")
        print("  m        — move pawn")
        print("  w        — place wall")
        print("  q        — quit")
        choice = prompt("> ")

        if choice == 'q':
            print("Goodbye!")
            sys.exit(0)

        elif choice == 'm':
            # Attempt a pawn move — returns new state or None if cancelled/invalid
            new_state = do_pawn_move(state)
            if new_state:
                return new_state   # valid move made, end the human's turn

        elif choice == 'w':
            # Attempt a wall placement — returns new state or None if cancelled/invalid
            new_state = do_wall_move(state)
            if new_state:
                return new_state   # valid wall placed, end the human's turn

        else:
            print("Type m, w, or q.\n")


def do_pawn_move(state):
    """
    Handle the player selecting and confirming a pawn destination.

    Flow:
        1. Get all legal pawn moves from board.py
        2. Show them to the player (highlighted on board)
        3. Wait for player to pick one
        4. Validate and apply via movePawn()
        5. Return new state, or None if player cancelled

    Frontend equivalent:
        1. On pawn click → call getLegalPawnMoves() → highlight those cells
        2. On valid cell click → call movePawn(state, 'x', board_row, board_col)
        3. If movePawn returns a state → update UI, end human turn
        4. If movePawn returns None → show error (shouldn't happen if you
           only allow clicks on highlighted cells)

    Note on coordinates:
        getLegalPawnMoves returns BOARD coords (0-16).
        Display coords (0-8) = board coords // 2.
        movePawn() takes BOARD coords.
    """
    board      = state['board']

    # Get all valid destinations in board coords (0-16)
    legal      = getLegalPawnMoves(board, 'x')

    # Convert to display format: col letter (A-I) and row number (1-9)
    legal_disp = [f"{chr(65 + c//2)}{r//2 + 1}" for r, c in legal]

    print(f"\nLegal moves: {', '.join(legal_disp)}")

    # Re-render board with valid cells highlighted as '*'
    # render() expects BOARD coords in highlights, not display coords
    render(state, highlights=legal)

    while True:
        raw = prompt("Enter destination as col+row e.g. E3 (or 'b' to go back): ").upper()
        if raw == 'B':
            return None   # player cancelled

        # Parse letter+number format e.g. "E3"
        if len(raw) == 2 and raw[0].isalpha() and raw[1].isdigit():
            gc = ord(raw[0]) - 65        # A=0 ... I=8
            gr = int(raw[1]) - 1         # 1-indexed → 0-indexed
        elif len(raw) == 3 and raw[0].isalpha() and raw[1:].isdigit():
            gc = ord(raw[0]) - 65
            gr = int(raw[1:]) - 1
        else:
            print("Bad input. Try: E3 or D4")
            continue

        if not (0 <= gr <= 8 and 0 <= gc <= 8):
            print("Out of range. Rows 1-9, cols A-I.")
            continue

        # Convert display coords to board coords for movePawn()
        br, bc = board_to_grid(gr, gc)

        new_state = movePawn(state, 'x', br, bc)
        if new_state is None:
            print(f"Illegal move. Legal moves are: {', '.join(legal_disp)}")
            continue

        return new_state


def do_wall_move(state):
    """
    Handle the player placing a wall.

    Wall coordinate system:
        The player specifies the TOP-LEFT corner of the wall in display coords.

        H wall at display (row, col):
            Blocks the gap BELOW display row N.
            Board anchor = (row*2 + 1, col*2)   — an odd board row
            Occupies board cells: (row*2+1, col*2), (row*2+1, col*2+1), (row*2+1, col*2+2)

        V wall at display (row, col):
            Blocks the gap to the RIGHT of display col N.
            Board anchor = (row*2, col*2 + 1)   — an odd board col
            Occupies board cells: (row*2, col*2+1), (row*2+1, col*2+1), (row*2+2, col*2+1)

    Frontend equivalent:
        The player drags a wall piece and drops it on a gap between cells.
        From the drop position, determine:
            - Was it dropped on a horizontal gap? → orientation 'H'
            - Was it dropped on a vertical gap?   → orientation 'V'
        Then compute the anchor from the gap slot's row/col and call
        placeWall(state, 'x', anchor, orientation).

    placeWall() returns:
        New state dict  → wall was valid, update UI
        None            → wall was invalid (overlaps, traps a player, out of bounds)
    """
    print("\nWall placement:")
    print("  Use column letter (A-I) and row number (1-9)")
    print("  H wall: blocks the gap BELOW row N, starting at col X")
    print("  V wall: blocks the gap RIGHT OF col X, starting at row N")
    print("  Example: 'E3 H'  blocks below row 3 at col E")
    print("           'C5 V'  blocks right of col C at row 5")
    print("  (or 'b' to go back)")

    while True:
        raw = prompt("Enter: colrow H/V  e.g. E3 H > ").upper()
        if raw == 'B':
            return None

        parts = raw.split()
        if len(parts) != 2:
            print("Need col+row and orientation, e.g.: E3 H")
            continue

        pos = parts[0]
        ori = parts[1]

        # Parse col letter + row number e.g. "E3"
        if len(pos) == 2 and pos[0].isalpha() and pos[1].isdigit():
            gc = ord(pos[0]) - 65        # A=0 ... I=8
            gr = int(pos[1]) - 1         # 1-indexed → 0-indexed
        elif len(pos) == 3 and pos[0].isalpha() and pos[1:].isdigit():
            gc = ord(pos[0]) - 65
            gr = int(pos[1:]) - 1
        else:
            print("Bad position. Try: E3 or D4")
            continue

        if not (0 <= gr <= 8 and 0 <= gc <= 8):
            print("Out of range. Rows 1-9, cols A-I.")
            continue

        if ori not in ('H', 'V'):
            print("Orientation must be H or V.")
            continue

        # Convert display coords to board anchor coords
        # H wall: sits in the odd row BELOW display row gr → board row = gr*2 + 1
        # V wall: sits in the odd col RIGHT OF display col gc → board col = gc*2 + 1
        if ori == 'H':
            anchor = (gr * 2 + 1, gc * 2)    # odd board row, even board col
        else:
            anchor = (gr * 2, gc * 2 + 1)    # even board row, odd board col

        new_state = placeWall(state, 'x', anchor, ori)
        if new_state is None:
            print("Invalid wall — blocked, out of bounds, or would trap a player. Try again.")
            continue

        return new_state


# ─────────────────────────────────────────────────────────────
# MAIN GAME LOOP
#
# Frontend equivalent:
#   This is your top-level game controller.
#   Replace the while loop with your framework's event loop.
#   Replace render() with your drawBoard() / updateUI() calls.
#   Replace human_turn() with your click/drag event handlers.
#   The AI section stays the same — just call get_ai_move(state)
#   and apply the returned move.
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 44)
    print("           QUORIDOR — Terminal")
    print("  You = W  (row 1, moving DOWN to row 9)")
    print("  CPU = B  (row 9, moving UP  to row 1)")
    print("  Cols: A-I   Rows: 1-9")
    print("=" * 44)

    # initGame() returns the starting state dict:
    #   x at display (0,4) = board (0,8)
    #   o at display (8,4) = board (16,8)
    #   both have 10 walls
    #   current_player = 'x' (human goes first)
    state = initGame()

    # Track the AI's previous position to prevent oscillation
    # (AI going back and forth between two cells)
    # Reset to None after a wall move — only relevant for pawn moves
    last_ai_pos = None

    while True:

        # ── Render current board ──────────────────────────────
        # Frontend: call your drawBoard(state) here
        render(state)

        # ── Check for winner ──────────────────────────────────
        # state['winner'] is set by movePawn() when a pawn reaches goal row
        # 'x' wins at board row 16 (display row 8)
        # 'o' wins at board row 0  (display row 0)
        if state['winner']:
            if state['winner'] == 'x':
                print("YOU WIN! Congratulations.")
            else:
                print("CPU WINS. Better luck next time.")
            break   # end the game loop

        # ── Human turn ───────────────────────────────────────
        if state['current_player'] == 'x':
            # human_turn() blocks until the human makes a valid move
            # returns the new state with current_player switched to 'o'
            # Frontend: replace with your event-driven input handler
            state = human_turn(state)

        # ── AI turn ──────────────────────────────────────────
        else:
            print("CPU is thinking...")

            # Remember where the AI currently is before it moves
            # Used for oscillation detection in get_ai_move()
            prev_ai_pos = findPawn(state['board'], 'o')

            # get_ai_move() runs MCTS and returns the best move as a dict:
            #   Pawn move: {'type': 'pawn', 'target': (board_row, board_col)}
            #   Wall move: {'type': 'wall', 'anchor': (board_row, board_col),
            #               'orientation': 'H' or 'V'}
            # last_ai_pos prevents the AI from going back to its previous cell
            move = get_ai_move(state, last_ai_pos=last_ai_pos)

            if move['type'] == 'pawn':
                r, c  = move['target']   # board coords
                state = movePawn(state, 'o', r, c)
                last_ai_pos = prev_ai_pos
                # Convert board coords to A-I / 1-9 for display
                col_letter = chr(65 + c // 2)   # 0→A, 1→B ... 8→I
                row_number = r // 2 + 1          # 0→1 ... 8→9
                print(f"CPU moved pawn to {col_letter}{row_number}")

            else:
                state = placeWall(state, 'o', move['anchor'], move['orientation'])
                last_ai_pos = None
                ar, ac = move['anchor']
                # Convert board anchor to display coords for logging
                col_letter = chr(65 + ac // 2)
                row_number = ar // 2 + 1
                print(f"CPU placed {move['orientation']} wall at {col_letter}{row_number}")


if __name__ == '__main__':
    main()