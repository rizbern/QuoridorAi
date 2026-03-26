"""
backend/bfs.py

NOTE: Core BFS logic now lives directly on the Board class in board.py:
  - board._bfs_has_path(player)  → used internally to validate wall placement
  - board.bfs_distance(player)   → returns shortest path length, used by MCTS

This file provides standalone BFS utilities that MCTS can import directly
for rollout heuristics without needing a full Board instance.
"""

from collections import deque


def bfs_distance(pawns: dict, walls: set, player: int, board_size: int = 9) -> int:
    """
    Standalone BFS: returns the shortest path (in steps) from the player's
    current position to their goal row.

    player 1 → goal is row 0    (started at bottom, moving up)
    player 2 → goal is row 8    (started at top, moving down)

    Parameters:
        pawns   : { 1: (row, col), 2: (row, col) }
        walls   : set of (row, col, orientation) tuples
        player  : 1 or 2
        board_size: size of the board (default 9)

    Returns:
        int — number of steps to goal row, or float('inf') if no path
    """
    goal_row = 0 if player == 1 else board_size - 1
    start = pawns[player]

    visited = set()
    queue = deque()
    queue.append((start, 0))   # (position, distance)
    visited.add(start)

    while queue:
        (row, col), dist = queue.popleft()

        if row == goal_row:
            return dist

        for neighbor in _get_neighbors(row, col, walls, board_size):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))

    return float('inf')


def bfs_has_path(pawns: dict, walls: set, player: int, board_size: int = 9) -> bool:
    """
    Standalone BFS: returns True if the player has any path to their goal row.
    Used inside board.is_valid_wall() to validate wall placements.
    """
    return bfs_distance(pawns, walls, player, board_size) < float('inf')


def _get_neighbors(row: int, col: int, walls: set, board_size: int) -> list:
    """
    Returns all cells reachable from (row, col) given the current wall set.
    Checks each of the 4 directions and whether a wall blocks that edge.
    """
    neighbors = []

    directions = [
        (-1,  0),  # Up
        ( 1,  0),  # Down
        ( 0, -1),  # Left
        ( 0,  1),  # Right
    ]

    for dr, dc in directions:
        nr, nc = row + dr, col + dc

        # Boundary check
        if not (0 <= nr < board_size and 0 <= nc < board_size):
            continue

        # Wall check
        if _is_wall_between(row, col, nr, nc, walls):
            continue

        neighbors.append((nr, nc))

    return neighbors


def _is_wall_between(r1: int, c1: int, r2: int, c2: int, walls: set) -> bool:
    """
    Returns True if there is a wall blocking movement between adjacent
    cells (r1,c1) and (r2,c2).

    Wall coordinate convention:
      H wall at (r, c): blocks vertical movement between rows r and r+1,
                        covering columns c and c+1
      V wall at (r, c): blocks horizontal movement between cols c and c+1,
                        covering rows r and r+1
    """
    # Moving DOWN (r2 = r1+1)
    if r2 == r1 + 1 and c2 == c1:
        return (r1, c1,     "H") in walls or \
               (r1, c1 - 1, "H") in walls

    # Moving UP (r2 = r1-1)
    if r2 == r1 - 1 and c2 == c1:
        return (r2, c1,     "H") in walls or \
               (r2, c1 - 1, "H") in walls

    # Moving RIGHT (c2 = c1+1)
    if r2 == r1 and c2 == c1 + 1:
        return (r1, c1,     "V") in walls or \
               (r1 - 1, c1, "V") in walls

    # Moving LEFT (c2 = c1-1)
    if r2 == r1 and c2 == c1 - 1:
        return (r1, c2,     "V") in walls or \
               (r1 - 1, c2, "V") in walls

    return False