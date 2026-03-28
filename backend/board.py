import copy
import random

BOARD_SIZE = 9

class Board:
    def __init__(self):
        self.pawns = {
            1: (8, 4),
            2: (0, 4)
        }

        # (row, col, orientation)
        # "H" blocks movement between row and row+1
        # "V" blocks movement between col and col+1
        # (row, col) is the TOP-LEFT corner of the 2-cell wall segment
        self.walls = set() # Actuall wall placed loc

        self.remaining_walls = {
            1: 10,
            2: 10
        }

        # Track whose turn it is
        self.current_player = self.select_starting_player()

    def select_starting_player(self):
        return random.randint(1, 2)

    def clone(self):
        # copying board for mcts sim
        return copy.deepcopy(self)

    def is_inside(self, row, col):
        # return through if within the 9x9 board
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

    def is_wall_between(self, r1, c1, r2, c2):
        """
        returns true for followwing cases:
        For a HORIZONTAL wall (row, col, "H"):
            Blocks movement between (row, col)<->(row+1, col)
                                and (row, col+1)<->(row+1, col+1)

        For a VERTICAL wall (row, col, "V"):
            Blocks movement between (row, col)<->(row, col+1)
                                and (row+1, col)<->(row+1, col+1)
        """
        # Moving DOWN: r2 = r1+1, c2 = c1
        if r2 == r1 + 1 and c2 == c1:
            return (r1, c1,     "H") in self.walls or \
                   (r1, c1 - 1, "H") in self.walls

        # Moving UP: r2 = r1-1, c2 = c1
        if r2 == r1 - 1 and c2 == c1:
            return (r2, c1,     "H") in self.walls or \
                   (r2, c1 - 1, "H") in self.walls

        # Moving RIGHT: r2 = r1, c2 = c1+1
        if r2 == r1 and c2 == c1 + 1:
            return (r1, c1,     "V") in self.walls or \
                   (r1 - 1, c1, "V") in self.walls

        # Moving LEFT: r2 = r1, c2 = c1-1
        if r2 == r1 and c2 == c1 - 1:
            return (r1, c2,     "V") in self.walls or \
                   (r1 - 1, c2, "V") in self.walls

        return False

    def get_neighbors(self, row, col):
        """
        Returns all cells reachable from (row, col) without crossing a wall.
        Used by BFS and pawn move validation.
        """
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if self.is_inside(nr, nc) and not self.is_wall_between(row, col, nr, nc):
                neighbors.append((nr, nc))
        return neighbors

    # -------------------------------------------------------------------------
    # Pawn movement
    # -------------------------------------------------------------------------

    def get_valid_pawn_moves(self, player):
        """
        Returns all valid positions the pawn can move to.
        Handles normal moves AND jump-over logic when pawns are adjacent.
        """
        opponent = 2 if player == 1 else 1
        row, col = self.pawns[player]
        opp_row, opp_col = self.pawns[opponent]

        valid_moves = []

        for nr, nc in self.get_neighbors(row, col):
            # Normal move — destination is not occupied by opponent
            if (nr, nc) != (opp_row, opp_col):
                valid_moves.append((nr, nc))

            else:
                # Opponent is on this neighbor — attempt jump
                # Try to jump straight over the opponent
                jump_r = opp_row + (opp_row - row)
                jump_c = opp_col + (opp_col - col)

                if (self.is_inside(jump_r, jump_c) and
                        not self.is_wall_between(opp_row, opp_col, jump_r, jump_c)):
                    # Straight jump is clear
                    valid_moves.append((jump_r, jump_c))
                else:
                    # Straight jump blocked by wall or boundary — try diagonal jumps
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        diag_r = opp_row + dr
                        diag_c = opp_col + dc
                        # Must not go back where we came from
                        if (diag_r, diag_c) == (row, col):
                            continue
                        if (self.is_inside(diag_r, diag_c) and
                                not self.is_wall_between(opp_row, opp_col, diag_r, diag_c)):
                            valid_moves.append((diag_r, diag_c))

        return valid_moves

    def move_pawn(self, player, position):
        """Moves the pawn if the position is valid. Returns True on success."""
        if position in self.get_valid_pawn_moves(player):
            self.pawns[player] = position
            return True
        return False

    # -------------------------------------------------------------------------
    # Wall placement
    # -------------------------------------------------------------------------

    def is_valid_wall(self, row, col, orientation):
        """
        Checks if a wall placement at (row, col, orientation) is legal:
        1. Within bounds (walls live on intersections, max index is 7)
        2. Doesn't overlap or cross an existing wall
        3. Doesn't completely block either player's path (uses BFS)
        """
        # Walls can only be placed at rows/cols 0-7 (each wall spans 2 cells)
        if not (0 <= row <= BOARD_SIZE - 2 and 0 <= col <= BOARD_SIZE - 2):
            return False

        # Already occupied (CHeck if wall already is placed there)
        if (row, col, orientation) in self.walls:
            return False

        # Check crossing/overlapping walls
        if orientation == "H":
            # A horizontal wall at (r,c) overlaps with (r, c-1, H) and (r, c+1, H)
            # and crosses a vertical wall at (r, c, V)
            if (row, col - 1, "H") in self.walls:
                return False
            if (row, col + 1, "H") in self.walls:
                return False
            if (row, col, "V") in self.walls:
                return False

        elif orientation == "V":
            if (row - 1, col, "V") in self.walls:
                return False
            if (row + 1, col, "V") in self.walls:
                return False
            if (row, col, "H") in self.walls:
                return False

        # Temporarily place the wall and use BFS to check both players still have a path
        self.walls.add((row, col, orientation))
        p1_ok = self._bfs_has_path(1)
        p2_ok = self._bfs_has_path(2)
        self.walls.remove((row, col, orientation))

        return p1_ok and p2_ok # if either false, then theres no path

    def _bfs_has_path(self, player):
        """
        BFS from player's current position to their goal row.
        Player 1 needs to reach row 0.
        Player 2 needs to reach row 8 (BOARD_SIZE - 1).
        Returns True if a path exists.
        """
        goal_row = 0 if player == 1 else BOARD_SIZE - 1
        start = self.pawns[player]

        visited = set()
        queue = [start]
        visited.add(start)

        while queue:
            row, col = queue.pop(0)

            if row == goal_row:
                return True # path exists, can palce wall

            for neighbor in self.get_neighbors(row, col):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return False # no path

    def bfs_distance(self, player):
        """
        Returns the shortest path length (in steps) from the player's
        current position to their goal row. Used as a heuristic in MCTS.
        Returns a large number if no path exists.
        """
        goal_row = 0 if player == 1 else BOARD_SIZE - 1
        start = self.pawns[player]

        visited = set()
        # Queue stores (position, distance)
        queue = [(start, 0)]
        visited.add(start)

        while queue:
            (row, col), dist = queue.pop(0)

            if row == goal_row:
                return dist

            for neighbor in self.get_neighbors(row, col):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))

        return float('inf')

    def place_wall(self, player, row, col, orientation):
        """Places a wall if valid. Returns True on success."""
        if self.remaining_walls[player] <= 0:
            return False
        if not self.is_valid_wall(row, col, orientation):
            return False

        self.walls.add((row, col, orientation))
        self.remaining_walls[player] -= 1
        return True

    # -------------------------------------------------------------------------
    # Game state
    # -------------------------------------------------------------------------

    def get_winner(self):
        """Player 1 wins by reaching row 0. Player 2 wins by reaching row 8."""
        if self.pawns[1][0] == 0:
            return 1
        if self.pawns[2][0] == BOARD_SIZE - 1:
            return 2
        return None

    def is_terminal(self):
        return self.get_winner() is not None

    # -------------------------------------------------------------------------
    # MCTS interface
    # -------------------------------------------------------------------------

    def get_legal_moves(self, player):
        """
        Returns all legal moves for a player as a list of tuples:
            ("move", (row, col))
            ("wall", (row, col, orientation))
        """
        moves = []

        # Pawn moves
        for pos in self.get_valid_pawn_moves(player):
            moves.append(("move", pos))

        # Wall placements (only if player has walls left)
        if self.remaining_walls[player] > 0:
            for row in range(BOARD_SIZE - 1):
                for col in range(BOARD_SIZE - 1):
                    for orientation in ["H", "V"]:
                        if self.is_valid_wall(row, col, orientation):
                            moves.append(("wall", (row, col, orientation)))

        return moves

    def apply_move(self, player, move):
        """
        Applies a move returned by get_legal_moves.
        Switches current_player after the move.
        """
        move_type, data = move

        if move_type == "move":
            self.move_pawn(player, data)

        elif move_type == "wall":
            row, col, orientation = data
            self.place_wall(player, row, col, orientation)

        # Switch turns
        self.current_player = 2 if player == 1 else 1