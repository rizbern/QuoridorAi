from collections import deque
from copy import deepcopy

BOARD_SIZE = 17
GOAL_ROW   = {'x': 16, 'o': 0}
OPPONENT   = {'x': 'o', 'o': 'x'}


def createBoard():
    return [list('.' * BOARD_SIZE) for _ in range(BOARD_SIZE)]


def initGame():
    board = createBoard()
    board[0][8]  = 'x'
    board[16][8] = 'o'
    return {
        'board':           board,
        'walls_remaining': {'x': 10, 'o': 10},
        'current_player':  'x',
        'winner':          None,
    }


def findPawn(board, player):
    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            if board[i][j] == player:
                return (i, j)
    return None


def checkWin(board, player):
    pos = findPawn(board, player)
    if pos is None:
        return False
    return pos[0] == GOAL_ROW[player]


def bfsDistance(board, player):
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
    return None


def _pawnNeighbors(board, r, c):
    neighbors  = []
    directions = [('UP', -1, 0), ('DOWN', +1, 0), ('LEFT', 0, -1), ('RIGHT', 0, +1)]
    for direction, dr, dc in directions:
        wr = r + dr
        wc = c + dc
        if not (0 <= wr < BOARD_SIZE and 0 <= wc < BOARD_SIZE):
            continue
        if _wallBlocks(board, r, c, direction):
            continue
        nr = r + 2 * dr
        nc = c + 2 * dc
        if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
            continue
        if board[nr][nc] in ('x', 'o'):
            jr = nr + 2 * dr
            jc = nc + 2 * dc
            straight_blocked  = _wallBlocks(board, nr, nc, direction)
            straight_inbounds = (0 <= jr < BOARD_SIZE and 0 <= jc < BOARD_SIZE)
            if not straight_blocked and straight_inbounds:
                neighbors.append((jr, jc))
            else:
                for perp_dir, pdr, pdc in _perpendiculars(direction):
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
    if direction in ('UP', 'DOWN'):
        return [('LEFT', 0, -1), ('RIGHT', 0, +1)]
    return [('UP', -1, 0), ('DOWN', +1, 0)]


def pathExists(board, player):
    return bfsDistance(board, player) is not None


def getLegalPawnMoves(board, player):
    pos = findPawn(board, player)
    if pos is None:
        return []
    return _pawnNeighbors(board, pos[0], pos[1])


def movePawn(state, player, target_row, target_col):
    board = state['board']
    legal = getLegalPawnMoves(board, player)
    if (target_row, target_col) not in legal:
        return None
    new_state = deepcopy(state)
    b = new_state['board']
    old_r, old_c = findPawn(b, player)
    b[old_r][old_c]           = '.'
    b[target_row][target_col] = player
    if target_row == GOAL_ROW[player]:
        new_state['winner'] = player
    new_state['current_player'] = OPPONENT[player]
    return new_state


def isValidWallPlacement(board, walls_remaining, player, anchor, orientation):
    i, j = anchor
    if walls_remaining[player] <= 0:
        return False, "No walls remaining"
    if orientation == 'H':
        if i % 2 == 0 or j % 2 != 0:
            return False, "Invalid anchor for H wall"
        if j + 2 >= BOARD_SIZE:
            return False, "Out of bounds"
        if board[i][j] != '.' or board[i][j+1] != '.' or board[i][j+2] != '.':
            return False, "Wall overlaps existing wall"
    elif orientation == 'V':
        if i % 2 != 0 or j % 2 == 0:
            return False, "Invalid anchor for V wall"
        if i + 2 >= BOARD_SIZE:
            return False, "Out of bounds"
        if board[i][j] != '.' or board[i+1][j] != '.' or board[i+2][j] != '.':
            return False, "Wall overlaps existing wall"
    else:
        return False, "Unknown orientation"
    test_board = [row[:] for row in board]
    _applyWall(test_board, anchor, orientation)
    if not pathExists(test_board, 'x'):
        return False, "Wall would trap x"
    if not pathExists(test_board, 'o'):
        return False, "Wall would trap o"
    return True, "OK"


def _applyWall(board, anchor, orientation):
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
    board           = state['board']
    walls_remaining = state['walls_remaining']
    valid, reason   = isValidWallPlacement(board, walls_remaining, player, anchor, orientation)
    if not valid:
        return None
    new_state = deepcopy(state)
    _applyWall(new_state['board'], anchor, orientation)
    new_state['walls_remaining'][player] -= 1
    new_state['current_player'] = OPPONENT[player]
    return new_state


def _isValidWallFast(board, walls_remaining, player, anchor, orientation):
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