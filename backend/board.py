# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from collections import deque
from copy import deepcopy

# ─────────────────────────────────────────────────────────────
# Board is a 17×17 grid.
# Even rows/cols  → pawn cells  (0,2,4,...,16)
# Odd  rows       → H-wall rows (1,3,5,...,15)
# Odd  cols       → V-wall cols (1,3,5,...,15)
# Mixed (odd,odd) → wall intersections
#
# Walls occupy 3 cells:
#   H wall at anchor (i,j):  (i,j)  (i,j+1)  (i,j+2)   — i odd, j even
#   V wall at anchor (i,j):  (i,j)  (i+1,j)  (i+2,j)   — i even, j odd
#
# Players:  'x' starts at (0,8),  goal = row 16
#            'o' starts at (16,8), goal = row 0
# ─────────────────────────────────────────────────────────────

BOARD_SIZE = 17

# Goal rows for each player
GOAL_ROW = {'x': 16, 'o': 0}

# Opponent map
OPPONENT = {'x': 'o', 'o': 'x'}


# ─────────────────────────────────────────────────────────────
# Board creation & init
# ─────────────────────────────────────────────────────────────

def createBoard():
    return [list('.' * BOARD_SIZE) for _ in range(BOARD_SIZE)]


def initGame():
    """Return a fresh game state dict."""
    board = createBoard()
    board[0][8]  = 'x'   # x starts top-center
    board[16][8] = 'o'   # o starts bottom-center
    return {
        'board':          board,
        'walls_remaining': {'x': 10, 'o': 10},
        'current_player': 'x',
        'winner':         None,
    }


# ─────────────────────────────────────────────────────────────
# Pawn helpers
# ─────────────────────────────────────────────────────────────

def findPawn(board, player):
    """Return (row, col) of player's pawn, or None."""
    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            if board[i][j] == player:
                return (i, j)
    return None


def checkWin(board, player):
    """True if player has reached their goal row."""
    pos = findPawn(board, player)
    if pos is None:
        return False
    return pos[0] == GOAL_ROW[player]


# ─────────────────────────────────────────────────────────────
# BFS — used for path validation AND heuristic eval later
# ─────────────────────────────────────────────────────────────

def bfsDistance(board, player):
    """
    Return the shortest pawn-step distance from player's current
    position to any cell in their goal row.
    Returns None if no path exists (wall fully blocks).
    """
    start    = findPawn(board, player)
    goal_row = GOAL_ROW[player]
    if start is None:
        return None

    visited = set()
    queue   = deque()
    queue.append((start[0], start[1], 0))
    visited.add(start)

    while queue:
        r, c, dist = queue.popleft()

        if r == goal_row:
            return dist

        for nr, nc in _pawnNeighbors(board, r, c):
            if (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append((nr, nc, dist + 1))

    return None   # completely blocked


def _pawnNeighbors(board, r, c):
    """
    All cells reachable by a pawn from (r,c) in one move,
    including jump-overs and diagonal jumps.
    Ignores whose pawn is where — just geometry.
    """
    neighbors = []
    # Cardinal directions: (dr, dc, wall_row_offset, wall_col_offset)
    # wall sits at (r+wr, c+wc) between (r,c) and (r+2*dr, c+2*dc)
    directions = [
        ('UP',    -1,  0),
        ('DOWN',  +1,  0),
        ('LEFT',   0, -1),
        ('RIGHT',  0, +1),
    ]

    for direction, dr, dc in directions:
        # Wall cell is between current cell and next cell
        wr = r + dr   # wall row
        wc = c + dc   # wall col

        # Check bounds for wall cell
        if not (0 <= wr < BOARD_SIZE and 0 <= wc < BOARD_SIZE):
            continue

        # Check if wall blocks this direction
        if _wallBlocks(board, r, c, direction):
            continue

        # Target pawn cell
        nr = r + 2 * dr
        nc = c + 2 * dc

        if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
            continue

        # Is target occupied by any pawn?
        if board[nr][nc] in ('x', 'o'):
            # Try to jump straight over
            jr = nr + 2 * dr
            jc = nc + 2 * dc
            straight_blocked = _wallBlocks(board, nr, nc, direction)
            straight_inbounds = (0 <= jr < BOARD_SIZE and 0 <= jc < BOARD_SIZE)

            if not straight_blocked and straight_inbounds:
                neighbors.append((jr, jc))
            else:
                # Diagonal jumps: try the two perpendicular directions
                perps = _perpendiculars(direction)
                for perp_dir, pdr, pdc in perps:
                    if _wallBlocks(board, nr, nc, perp_dir):
                        continue
                    diag_r = nr + 2 * pdr
                    diag_c = nc + 2 * pdc
                    if 0 <= diag_r < BOARD_SIZE and 0 <= diag_c < BOARD_SIZE:
                        neighbors.append((diag_r, diag_c))
        else:
            neighbors.append((nr, nc))

    return neighbors


def _wallBlocks(board, r, c, direction):
    """
    Returns True if there is a wall between cell (r,c)
    and the cell in the given direction.
    """
    if direction == 'UP':
        wr, wc = r - 1, c
        return 0 <= wr < BOARD_SIZE and board[wr][wc] == '-'
    if direction == 'DOWN':
        wr, wc = r + 1, c
        return 0 <= wr < BOARD_SIZE and board[wr][wc] == '-'
    if direction == 'LEFT':
        wr, wc = r, c - 1
        return 0 <= wc < BOARD_SIZE and board[wr][wc] == '|'
    if direction == 'RIGHT':
        wr, wc = r, c + 1
        return 0 <= wc < BOARD_SIZE and board[wr][wc] == '|'
    return False


def _perpendiculars(direction):
    """Return the two perpendicular (direction, dr, dc) tuples."""
    if direction in ('UP', 'DOWN'):
        return [('LEFT', 0, -1), ('RIGHT', 0, +1)]
    else:
        return [('UP', -1, 0), ('DOWN', +1, 0)]


def pathExists(board, player):
    """True if player has at least one path to their goal row."""
    return bfsDistance(board, player) is not None


# ─────────────────────────────────────────────────────────────
# Pawn movement
# ─────────────────────────────────────────────────────────────

def getLegalPawnMoves(board, player):
    """Return list of (row, col) cells the player can legally move to."""
    pos = findPawn(board, player)
    if pos is None:
        return []
    return _pawnNeighbors(board, pos[0], pos[1])


def movePawn(state, player, target_row, target_col):
    """
    Move player's pawn to (target_row, target_col).
    Returns updated state dict, or None if move is illegal.
    Mutates a deep copy — does NOT modify the original state.
    """
    board  = state['board']
    legal  = getLegalPawnMoves(board, player)

    if (target_row, target_col) not in legal:
        return None

    new_state = deepcopy(state)
    b = new_state['board']

    old_r, old_c = findPawn(b, player)
    b[old_r][old_c]          = '.'
    b[target_row][target_col] = player

    # Check win
    if target_row == GOAL_ROW[player]:
        new_state['winner'] = player

    new_state['current_player'] = OPPONENT[player]
    return new_state


# ─────────────────────────────────────────────────────────────
# Wall placement
# ─────────────────────────────────────────────────────────────

def isValidWallPlacement(board, walls_remaining, player, anchor, orientation):
    """
    Full validation:
      1. Player has walls left
      2. Anchor is in the correct position parity
      3. All 3 wall cells are empty
      4. No crossing wall at the intersection
      5. Neither player is completely cut off after placement (BFS check)
    """
    i, j = anchor

    # 1. Wall count
    if walls_remaining[player] <= 0:
        return False, "No walls remaining"

    if orientation == 'H':
        # anchor must be: odd row, even col
        if i % 2 == 0 or j % 2 != 0:
            return False, "Invalid anchor for H wall"
        # needs cells (i,j), (i,j+1), (i,j+2)
        if j + 2 >= BOARD_SIZE:
            return False, "Out of bounds"
        # 3. overlap
        if board[i][j] != '.' or board[i][j+1] != '.' or board[i][j+2] != '.':
            return False, "Wall overlaps existing wall"
        # 4. cross-check: a V wall crosses at (i-1,j+1)→(i+1,j+1) — center col j+1
        #    specifically a V wall occupying board[i][j+1] would block — already caught above
        #    cross means: V wall anchor at (i-1, j+1) which fills (i-1,j+1),(i,j+1),(i+1,j+1)
        #    board[i][j+1] already catches that. No extra check needed.

    elif orientation == 'V':
        # anchor must be: even row, odd col
        if i % 2 != 0 or j % 2 == 0:
            return False, "Invalid anchor for V wall"
        # needs cells (i,j), (i+1,j), (i+2,j)
        if i + 2 >= BOARD_SIZE:
            return False, "Out of bounds"
        # 3. overlap
        if board[i][j] != '.' or board[i+1][j] != '.' or board[i+2][j] != '.':
            return False, "Wall overlaps existing wall"
        # 4. cross-check already handled by overlap above

    else:
        return False, "Unknown orientation"

    # 5. BFS: simulate placement and check both players still have a path
    test_board = [row[:] for row in board]
    _applyWall(test_board, anchor, orientation)

    if not pathExists(test_board, 'x'):
        return False, "Wall would trap x"
    if not pathExists(test_board, 'o'):
        return False, "Wall would trap o"

    return True, "OK"


def _applyWall(board, anchor, orientation):
    """Write wall chars onto board in-place."""
    i, j = anchor
    if orientation == 'H':
        board[i][j]   = '-'
        board[i][j+1] = '-'
        board[i][j+2] = '-'
    elif orientation == 'V':
        board[i][j]   = '|'
        board[i+1][j] = '|'
        board[i+2][j] = '|'


def placeWall(state, player, anchor, orientation):
    """
    Place a wall for player.
    Returns updated state dict, or None if placement is illegal.
    Does NOT modify original state.
    """
    board           = state['board']
    walls_remaining = state['walls_remaining']

    valid, reason = isValidWallPlacement(board, walls_remaining, player, anchor, orientation)
    if not valid:
        return None

    new_state = deepcopy(state)
    _applyWall(new_state['board'], anchor, orientation)
    new_state['walls_remaining'][player] -= 1
    new_state['current_player'] = OPPONENT[player]
    return new_state


# ─────────────────────────────────────────────────────────────
# Legal moves (for AI / UI highlighting)
# ─────────────────────────────────────────────────────────────

def _isValidWallFast(board, walls_remaining, player, anchor, orientation):
    """Fast wall check skipping BFS — used by MCTS."""
    i, j = anchor
    if walls_remaining[player] <= 0:
        return False
    if orientation == 'H':
        if i % 2 == 0 or j % 2 != 0: return False
        if j + 2 >= BOARD_SIZE: return False
        if board[i][j] != '.' or board[i][j+1] != '.' or board[i][j+2] != '.': return False
    elif orientation == 'V':
        if i % 2 != 0 or j % 2 == 0: return False
        if i + 2 >= BOARD_SIZE: return False
        if board[i][j] != '.' or board[i+1][j] != '.' or board[i+2][j] != '.': return False
    else:
        return False
    return True


def getLegalMoves(state, player, fast=False):
    """
    Return all legal moves for player.
    fast=True  — skips BFS path check, used inside MCTS for speed.
    fast=False — full validation including BFS, used for final move execution.
    """
    board           = state['board']
    walls_remaining = state['walls_remaining']
    moves           = []

    for (r, c) in getLegalPawnMoves(board, player):
        moves.append({'type': 'pawn', 'target': (r, c)})

    if walls_remaining[player] > 0:
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                for ori in ('H', 'V'):
                    if fast:
                        valid = _isValidWallFast(board, walls_remaining, player, (i, j), ori)
                    else:
                        valid, _ = isValidWallPlacement(board, walls_remaining, player, (i, j), ori)
                    if valid:
                        moves.append({'type': 'wall', 'anchor': (i, j), 'orientation': ori})

    return moves


# ─────────────────────────────────────────────────────────────
# Quick smoke test
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    state = initGame()

    print("Starting positions:")
    print(f"  x at {findPawn(state['board'], 'x')}")
    print(f"  o at {findPawn(state['board'], 'o')}")

    # Move x down once
    state = movePawn(state, 'x', 2, 8)
    print(f"\nAfter x moves down: x at {findPawn(state['board'], 'x')}")

    # Place a horizontal wall
    state2 = placeWall(state, 'o', (3, 8), 'H')
    if state2:
        print(f"o placed H wall at (3,8). Walls left: {state2['walls_remaining']}")
        print(f"  BFS distance x to goal: {bfsDistance(state2['board'], 'x')}")
        print(f"  BFS distance o to goal: {bfsDistance(state2['board'], 'o')}")
    else:
        print("Wall placement failed")

    # Legal pawn moves for x
    pawn_moves = getLegalPawnMoves(state['board'], 'x')
    print(f"\nLegal pawn moves for x: {pawn_moves}")

    # Win check
    state3 = initGame()
    state3['board'][0][8] = '.'
    state3['board'][16][8] = 'x'
    print(f"\nWin check (x at row 16): {checkWin(state3['board'], 'x')}")