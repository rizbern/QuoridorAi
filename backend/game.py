# -*- coding: utf-8 -*-
import sys

from board import (
    initGame, findPawn, getLegalPawnMoves,
    movePawn, placeWall, checkWin, BOARD_SIZE
)
from ai import get_ai_move

# ─────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────

def render(state, highlights=None):
    board = state['board']
    wr    = state['walls_remaining']
    cp    = state['current_player']
    highlights = highlights or []

    print()
    print(f"  Walls — x: {wr['x']}  |  o: {wr['o']}      Turn: {'YOU (x)' if cp == 'x' else 'CPU (o)'}")
    print()

    # Column numbers (pawn cols: 0,2,4,6,8,10,12,14,16 → displayed as 0-8)
    print("     ", end="")
    for col in range(0, BOARD_SIZE, 2):
        print(f" {col//2} ", end="")
    print()
    print("     " + "---" * 9)

    for row in range(BOARD_SIZE):
        if row % 2 == 0:
            # Pawn row — show row number on left
            print(f" {row//2}  |", end="")
            for col in range(BOARD_SIZE):
                cell = board[row][col]
                if col % 2 == 0:
                    # Pawn cell
                    gRow = row // 2
                    gCol = col // 2
                    if (gRow, gCol) in highlights:
                        print(" * ", end="")
                    elif cell == 'x':
                        print(" X ", end="")
                    elif cell == 'o':
                        print(" O ", end="")
                    else:
                        print(" . ", end="")
                else:
                    # Vertical wall between cols
                    if cell == '|':
                        print("|", end="")
                    else:
                        print(" ", end="")
            print("|")
        else:
            # Wall row
            print("     |", end="")
            for col in range(BOARD_SIZE):
                cell = board[row][col]
                if col % 2 == 0:
                    if cell == '-':
                        print("---", end="")
                    else:
                        print("   ", end="")
                else:
                    # intersection: fill if both neighbors are walls
                    left  = board[row][col-1] == '-' if col > 0 else False
                    right = board[row][col+1] == '-' if col+1 < BOARD_SIZE else False
                    print("-" if (left and right) else " ", end="")
            print("|")

    print("     " + "---" * 9)
    print()


# ─────────────────────────────────────────────
# Input helpers
# ─────────────────────────────────────────────

def prompt(msg):
    return input(msg).strip().lower()


def parse_coord(s):
    """Parse 'row,col' or 'row col' into (int, int). Returns None on failure."""
    try:
        parts = s.replace(',', ' ').split()
        if len(parts) != 2:
            return None
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        return None


def board_to_grid(gr, gc):
    """Convert display coords (0-8) to board array coords (0,2,...,16)."""
    return gr * 2, gc * 2


# ─────────────────────────────────────────────
# Human turn
# ─────────────────────────────────────────────

def human_turn(state):
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
            new_state = do_pawn_move(state)
            if new_state:
                return new_state

        elif choice == 'w':
            new_state = do_wall_move(state)
            if new_state:
                return new_state

        else:
            print("Type m, w, or q.\n")


def do_pawn_move(state):
    board      = state['board']
    legal      = getLegalPawnMoves(board, 'x')
    legal_disp = [(r // 2, c // 2) for r, c in legal]

    print(f"\nLegal moves (row, col): {legal_disp}")
    render(state, highlights=legal)

    while True:
        raw = prompt("Enter destination row,col (or 'b' to go back): ")
        if raw == 'b':
            return None

        coord = parse_coord(raw)
        if coord is None:
            print("Bad input. Try: 4 4")
            continue

        br, bc = board_to_grid(*coord)
        new_state = movePawn(state, 'x', br, bc)
        if new_state is None:
            print(f"Illegal move. Legal moves are: {legal_disp}")
            continue

        return new_state


def do_wall_move(state):
    print("\nWall placement:")
    print("  Anchor is the TOP-LEFT corner of the wall in display coords (0-8)")
    print("  H wall blocks movement between row N and row N+1")
    print("  V wall blocks movement between col N and col N+1")
    print("  Example: 'w 3 4 H'  or  'w 2 2 V'")
    print("  (or 'b' to go back)")

    raw = prompt("Enter: row col H/V > ").upper()
    if raw == 'B':
        return None

    parts = raw.split()
    if len(parts) != 3:
        print("Need exactly 3 values: row col orientation\n")
        return None

    try:
        gr, gc = int(parts[0]), int(parts[1])
        ori    = parts[2]
    except ValueError:
        print("Bad input.\n")
        return None

    if ori not in ('H', 'V'):
        print("Orientation must be H or V.\n")
        return None

    # Convert display coords to board anchor coords
    if ori == 'H':
        # H wall anchor: odd row, even col
        # Display row gr means the gap BELOW pawn row gr
        # Board anchor row = gr*2 + 1, col = gc*2
        anchor = (gr * 2 + 1, gc * 2)
    else:
        # V wall anchor: even row, odd col
        # Board anchor row = gr*2, col = gc*2 + 1
        anchor = (gr * 2, gc * 2 + 1)

    new_state = placeWall(state, 'x', anchor, ori)
    if new_state is None:
        print("Invalid wall placement. Try again.\n")
        return None

    return new_state


# ─────────────────────────────────────────────
# Main game loop
# ─────────────────────────────────────────────

def main():
    print("=" * 40)
    print("         QUORIDOR — Terminal")
    print("  You = X (top, going DOWN to row 8)")
    print("  CPU = O (bottom, going UP to row 0)")
    print("=" * 40)

    state        = initGame()
    last_ai_pos  = None   # tracks AI's previous position to prevent oscillation

    while True:
        render(state)

        # Check win
        if state['winner']:
            if state['winner'] == 'x':
                print("YOU WIN! Congratulations.")
            else:
                print("CPU WINS. Better luck next time.")
            break

        if state['current_player'] == 'x':
            state = human_turn(state)
        else:
            print("CPU is thinking...")
            from board import findPawn
            prev_ai_pos = findPawn(state['board'], 'o')
            move = get_ai_move(state, last_ai_pos=last_ai_pos)

            if move['type'] == 'pawn':
                r, c  = move['target']
                state = movePawn(state, 'o', r, c)
                last_ai_pos = prev_ai_pos   # remember where we just were
                print(f"CPU moved pawn to ({r//2}, {c//2})")
            else:
                state = placeWall(state, 'o', move['anchor'], move['orientation'])
                last_ai_pos = None   # reset after wall — no oscillation concern
                ar, ac = move['anchor']
                print(f"CPU placed {move['orientation']} wall at anchor ({ar}, {ac})")


if __name__ == '__main__':
    main()