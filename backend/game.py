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

    Args:
        state:      the game state dict
        highlights: list of board coords [(row, col), ...] to mark as '*'
                    used to show valid pawn moves to the player

    Frontend notes:
        - Board cells are at even row + even col in the 17x17 grid
        - Horizontal walls are at odd row + even col (spans 3 cells wide)
        - Vertical walls are at even row + odd col (spans 3 cells tall)
        - Wall intersections are at odd row + odd col (purely visual)
        - highlights are in BOARD coords (not display coords)
    """
    board = state['board']
    wr    = state['walls_remaining']   # {'x': N, 'o': N}
    cp    = state['current_player']    # 'x' or 'o'
    highlights = highlights or []

    print()
    # Show wall counts and whose turn it is
    print(f"  Walls — x: {wr['x']}  |  o: {wr['o']}      Turn: {'YOU (x)' if cp == 'x' else 'CPU (o)'}")
    print()

    # Column header — display coords 0-8
    print("     ", end="")
    for col in range(0, BOARD_SIZE, 2):
        print(f" {col//2} ", end="")
    print()
    print("     " + "---" * 9)

    for row in range(BOARD_SIZE):

        if row % 2 == 0:
            # ── Pawn row (board rows 0,2,4,...,16 → display rows 0-8) ──
            # Each pawn row shows player tokens, empty cells, and vertical walls

            print(f" {row//2}  |", end="")  # display row number on left edge

            for col in range(BOARD_SIZE):
                cell = board[row][col]

                if col % 2 == 0:
                    # Even col → playable cell
                    gRow = row // 2   # display row
                    gCol = col // 2   # display col

                    if (gRow, gCol) in highlights:
                        print(" * ", end="")   # valid move target
                    elif cell == 'x':
                        print(" X ", end="")   # human pawn
                    elif cell == 'o':
                        print(" O ", end="")   # AI pawn
                    else:
                        print(" . ", end="")   # empty cell

                else:
                    # Odd col → vertical wall slot between two cells
                    # '|' means a wall segment is placed here
                    if cell == '|':
                        print("|", end="")
                    else:
                        print(" ", end="")     # no wall, open passage

            print("|")  # right edge

        else:
            # ── Wall row (board rows 1,3,5,...,15) ──
            # These rows only contain horizontal wall segments.
            # No pawns live here — purely walls and gaps.

            print("     |", end="")  # left edge (no row number)

            for col in range(BOARD_SIZE):
                cell = board[row][col]

                if col % 2 == 0:
                    # Even col → horizontal wall cell
                    # '-' means a wall segment is here
                    if cell == '-':
                        print("---", end="")
                    else:
                        print("   ", end="")   # no wall, open passage

                else:
                    # Odd col → wall intersection point
                    # Fill with '-' only if both neighboring cells are wall segments
                    # This makes wall rendering continuous: ---+--- instead of --- ---
                    left  = board[row][col-1] == '-' if col > 0 else False
                    right = board[row][col+1] == '-' if col+1 < BOARD_SIZE else False
                    print("-" if (left and right) else " ", end="")

            print("|")  # right edge

    print("     " + "---" * 9)
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

    # Get all valid destinations in board coords
    legal      = getLegalPawnMoves(board, 'x')

    # Convert to display coords just for showing the player
    legal_disp = [(r // 2, c // 2) for r, c in legal]

    print(f"\nLegal moves (row, col): {legal_disp}")

    # Re-render board with valid cells highlighted as '*'
    # highlights must be in BOARD coords, not display coords
    render(state, highlights=legal)

    while True:
        raw = prompt("Enter destination row,col (or 'b' to go back): ")
        if raw == 'b':
            return None   # player cancelled, go back to m/w/q menu

        coord = parse_coord(raw)
        if coord is None:
            print("Bad input. Try: 4 4")
            continue

        # Convert display coords to board coords for movePawn()
        br, bc = board_to_grid(*coord)

        # movePawn validates legality internally and returns None if illegal
        new_state = movePawn(state, 'x', br, bc)
        if new_state is None:
            print(f"Illegal move. Legal moves are: {legal_disp}")
            continue

        return new_state   # valid move — new state with updated pawn position


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
    print("  Anchor is the TOP-LEFT corner of the wall in display coords (0-8)")
    print("  H wall blocks movement between row N and row N+1")
    print("  V wall blocks movement between col N and col N+1")
    print("  Example: '3 4 H'  or  '2 2 V'")
    print("  (or 'b' to go back)")

    while True:
        raw = prompt("Enter: row col H/V > ").upper()
        if raw == 'B':
            return None   # player cancelled

        parts = raw.split()
        if len(parts) != 3:
            print("Need exactly 3 values, e.g.: 3 4 H")
            continue

        try:
            gr, gc = int(parts[0]), int(parts[1])   # display coords
            ori    = parts[2]                         # 'H' or 'V'
        except ValueError:
            print("Bad input — row and col must be numbers.")
            continue

        if ori not in ('H', 'V'):
            print("Orientation must be H or V.")
            continue

        # Convert display coords to board anchor coords
        # H wall: sits in the odd row BELOW display row gr
        # V wall: sits in the odd col to the RIGHT of display col gc
        if ori == 'H':
            anchor = (gr * 2 + 1, gc * 2)   # odd board row, even board col
        else:
            anchor = (gr * 2, gc * 2 + 1)   # even board row, odd board col

        # placeWall validates everything: bounds, overlap, path-blocking (BFS)
        new_state = placeWall(state, 'x', anchor, ori)
        if new_state is None:
            print("Invalid wall — blocked, out of bounds, or would trap a player. Try again.")
            continue

        return new_state   # wall placed successfully


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
    print("=" * 40)
    print("         QUORIDOR — Terminal")
    print("  You = X (top, going DOWN to row 8)")
    print("  CPU = O (bottom, going UP to row 0)")
    print("=" * 40)

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

                # Apply the AI's pawn move
                # movePawn switches current_player to 'x' after applying
                state = movePawn(state, 'o', r, c)

                # Store where AI just was so next turn it won't go back there
                last_ai_pos = prev_ai_pos

                # Display coords for logging (board // 2)
                print(f"CPU moved pawn to ({r//2}, {c//2})")

            else:
                # AI chose to place a wall
                # placeWall switches current_player to 'x' after applying
                state = placeWall(state, 'o', move['anchor'], move['orientation'])

                # Reset oscillation tracking — not relevant after a wall move
                last_ai_pos = None

                # Log the wall placement in board coords
                ar, ac = move['anchor']
                print(f"CPU placed {move['orientation']} wall at anchor ({ar}, {ac})")


if __name__ == '__main__':
    main()