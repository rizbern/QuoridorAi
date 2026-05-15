import sys
from board import (
    initGame, findPawn, getLegalPawnMoves,
    movePawn, placeWall, checkWin, BOARD_SIZE
)
from ai import get_ai_move


def render(state, highlights=None):
    board      = state['board']
    wr         = state['walls_remaining']
    cp         = state['current_player']
    highlights = highlights or []

    print()
    print(f"  Walls — W: {wr['x']}  |  B: {wr['o']}      "
          f"Turn: {'YOU (W)' if cp == 'x' else 'CPU (B)'}")
    print()

    col_labels = "   " + "  ".join(f"  {chr(65+i)} " for i in range(9))
    print(col_labels)

    border = "   +" + "+".join(["---"] * 9) + "+"
    print(border)

    for row in range(BOARD_SIZE):
        if row % 2 == 0:
            display_row = row // 2 + 1
            line = f"{display_row:2d} |"
            for col in range(BOARD_SIZE):
                cell = board[row][col]
                if col % 2 == 0:
                    if (row, col) in highlights:
                        line += " * "
                    elif cell == 'x':
                        line += " W "
                    elif cell == 'o':
                        line += " B "
                    else:
                        line += " . "
                else:
                    line += "|" if cell == '|' else "+"
            line += "|"
            print(line)
        else:
            line = "   +"
            for col in range(BOARD_SIZE):
                cell = board[row][col]
                if col % 2 == 0:
                    line += "---" if cell == '-' else "   "
                else:
                    line += "+"
            print(line)

    print(border)
    print()


def prompt(msg):
    return input(msg).strip().lower()


def parse_col_row(s):
    s = s.upper()
    if len(s) == 2 and s[0].isalpha() and s[1].isdigit():
        return ord(s[0]) - 65, int(s[1]) - 1
    if len(s) == 3 and s[0].isalpha() and s[1:].isdigit():
        return ord(s[0]) - 65, int(s[1:]) - 1
    return None, None


def board_to_grid(gr, gc):
    return gr * 2, gc * 2


def human_turn(state):
    while True:
        print("Your move:  m = move pawn   w = place wall   q = quit")
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
            print("Type m, w, or q.")


def do_pawn_move(state):
    board      = state['board']
    legal      = getLegalPawnMoves(board, 'x')
    legal_disp = [f"{chr(65 + c//2)}{r//2 + 1}" for r, c in legal]
    print(f"\nLegal moves: {', '.join(legal_disp)}")
    render(state, highlights=legal)
    while True:
        raw = prompt("Destination e.g. E3 (or b to go back): ").upper()
        if raw == 'B':
            return None
        gc, gr = parse_col_row(raw)
        if gc is None or not (0 <= gr <= 8 and 0 <= gc <= 8):
            print("Bad input. Try: E3")
            continue
        br, bc    = board_to_grid(gr, gc)
        new_state = movePawn(state, 'x', br, bc)
        if new_state is None:
            print(f"Illegal move. Legal: {', '.join(legal_disp)}")
            continue
        return new_state


def do_wall_move(state):
    print("\nWall: col+row then H or V  e.g. 'E3 H'  or  'C5 V'  (b to go back)")
    while True:
        raw   = prompt("> ").upper()
        if raw == 'B':
            return None
        parts = raw.split()
        if len(parts) != 2:
            print("Need col+row and orientation e.g. E3 H")
            continue
        gc, gr = parse_col_row(parts[0])
        ori    = parts[1]
        if gc is None or not (0 <= gr <= 8 and 0 <= gc <= 8):
            print("Bad position. Try: E3")
            continue
        if ori not in ('H', 'V'):
            print("Orientation must be H or V.")
            continue
        anchor    = (gr * 2 + 1, gc * 2) if ori == 'H' else (gr * 2, gc * 2 + 1)
        new_state = placeWall(state, 'x', anchor, ori)
        if new_state is None:
            print("Invalid wall — overlaps, out of bounds, or traps a player.")
            continue
        return new_state


def main():
    print("=" * 44)
    print("           QUORIDOR")
    print("  You = W  (row 1, going DOWN to row 9)")
    print("  CPU = B  (row 9, going UP  to row 1)")
    print("  Cols: A-I   Rows: 1-9")
    print("=" * 44)

    state       = initGame()
    last_ai_pos = None

    while True:
        render(state)

        if state['winner']:
            if state['winner'] == 'x':
                print("YOU WIN!")
            else:
                print("CPU WINS.")
            break

        if state['current_player'] == 'x':
            state = human_turn(state)
        else:
            print("CPU is thinking...")
            prev_ai_pos = findPawn(state['board'], 'o')
            move        = get_ai_move(state, last_ai_pos=last_ai_pos)

            if move['type'] == 'pawn':
                r, c        = move['target']
                state       = movePawn(state, 'o', r, c)
                last_ai_pos = prev_ai_pos
                print(f"CPU moved pawn to {chr(65 + c//2)}{r//2 + 1}")
            else:
                state       = placeWall(state, 'o', move['anchor'], move['orientation'])
                last_ai_pos = None
                ar, ac      = move['anchor']
                print(f"CPU placed {move['orientation']} wall at {chr(65 + ac//2)}{ar//2 + 1}")


if __name__ == '__main__':
    main()