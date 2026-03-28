import math
import random
from bfs import bfs_distance

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

SIMULATIONS   = 1000   # How many simulations to run per move
EXPLORATION   = 1.414  # UCB1 C constant (√2) — balances explore vs exploit
MAX_DEPTH     = 40     # Max moves per simulation before BFS scores the position
AI_PLAYER     = 2      # AI always plays as player 2
HUMAN_PLAYER  = 1


# ─────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────

class MCTSNode:
    """
    Represents one state in the search tree.

    Every node stores:
      - The board state at that point in the game
      - Which player is about to move FROM this node
      - The move that was applied to reach this node (None for root)
      - Tree pointers: parent + children
      - Stats: how many times visited, how many wins recorded
      - untried_actions: moves not yet expanded into child nodes
    """

    def __init__(self, board, player, parent=None, move=None):
        self.board           = board          # Board state at this node
        self.player          = player         # Player whose turn it is HERE
        self.parent          = parent         # Parent node (None for root)
        self.move            = move           # Move that led to this node

        self.children        = []             # Expanded child nodes
        self.visits          = 0              # Times this node was visited
        self.wins            = 0.0            # Wins accumulated (float for partial credit)

        # All possible moves from this state — shrinks as children are added
        self.untried_actions = board.get_legal_moves(player)
        random.shuffle(self.untried_actions)  # Randomise expansion order

    def is_fully_expanded(self):
        """True when every legal move has a corresponding child node."""
        return len(self.untried_actions) == 0

    def is_terminal(self):
        """True when the game is over at this node."""
        return self.board.is_terminal()

    def ucb1(self, exploration=EXPLORATION):
        """
        Upper Confidence Bound formula:

            UCB1 = (wins / visits) + C * sqrt(ln(parent_visits) / visits)
                    ───────────────   ─────────────────────────────────────
                    exploitation         exploration

        Exploitation term: how often this node leads to a win.
        Exploration term:  how underexplored this node is relative to its parent.
        C constant:        controls the balance. √2 is the standard choice.

        A node that wins often AND hasn't been visited much scores highest.
        """
        if self.visits == 0:
            return float('inf')   # Unvisited nodes are always explored first

        exploitation = self.wins / self.visits
        exploration  = exploration * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )
        return exploitation + exploration

    def best_child(self):
        """Returns the child with the highest UCB1 score."""
        return max(self.children, key=lambda c: c.ucb1())

    def most_visited_child(self):
        """
        Returns the child visited most often.
        Used at the END of search to pick the final move —
        most visits = most confident, not just highest win rate.
        """
        return max(self.children, key=lambda c: c.visits)


# ─────────────────────────────────────────────
# The 4 MCTS phases
# ─────────────────────────────────────────────

def select(node):
    """
    PHASE 1 — SELECTION

    Starting from the root, walk DOWN the tree by always picking
    the child with the highest UCB1 score — until we reach a node
    that either:
      (a) Has untried actions left (not fully expanded), OR
      (b) Is a terminal node (game over)

    Think of it as: follow the most promising path already known,
    until you find somewhere new to explore.
    """
    while not node.is_terminal():
        if not node.is_fully_expanded():
            return node        # Found a node we can expand — stop here
        node = node.best_child()   # Fully expanded → go deeper
    return node


def expand(node):
    """
    PHASE 2 — EXPANSION

    Take one untried action from the current node, apply it to a
    cloned board, and create a new child node for that state.

    We only add ONE child per iteration — not all of them at once.
    This is critical for Quoridor because there are ~100+ possible
    moves per turn. Expanding all at once would flood memory before
    any simulation even runs.

    The next player is whoever isn't moving now.
    """
    action      = node.untried_actions.pop()   # Take one unexplored move
    new_board   = node.board.clone()           # Clone so we never touch real game
    new_board.apply_move(node.player, action)  # Apply the move to the clone

    next_player = HUMAN_PLAYER if node.player == AI_PLAYER else AI_PLAYER

    child = MCTSNode(
        board  = new_board,
        player = next_player,
        parent = node,
        move   = action
    )
    node.children.append(child)
    return child


def simulate(node):
    """
    PHASE 3 — SIMULATION (Rollout)

    From the newly expanded node, play the game forward using a
    BFS heuristic strategy until either:
      - The game reaches a terminal state (someone wins), OR
      - We hit MAX_DEPTH moves (then score the position with BFS)

    BFS heuristic strategy (smarter than pure random):
      At each step, 70% chance → pick the move that most reduces
      YOUR distance to goal. 30% chance → pick randomly.
      This biases play toward winning without being fully deterministic.

    Scoring:
      - Terminal win for AI  → 1.0  (full win)
      - Terminal win for human → 0.0  (full loss)
      - Depth limit hit → score based on BFS distances (see _bfs_score)

    Returns a float between 0.0 and 1.0 from the AI's perspective.
    """
    board  = node.board.clone()    # Never simulate on the real node board
    player = node.player           # Whose turn it is at the start of rollout

    for _ in range(MAX_DEPTH):
        if board.is_terminal():
            break

        moves = board.get_legal_moves(player)
        if not moves:
            break

        # 70% of the time: pick the heuristically best move
        # 30% of the time: pick randomly (keeps exploration alive)
        if random.random() < 0.7:
            move = _best_heuristic_move(board, player, moves)
        else:
            move = random.choice(moves)

        board.apply_move(player, move)
        player = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER

    # Score the result
    winner = board.get_winner()
    if winner == AI_PLAYER:
        return 1.0
    elif winner == HUMAN_PLAYER:
        return 0.0
    else:
        # Game not finished — use BFS distances to estimate who is winning
        return _bfs_score(board)


def backpropagate(node, result):
    """
    PHASE 4 — BACKPROPAGATION

    Walk back UP the tree from the simulated node to the root,
    updating every ancestor's visit count and win count.

    The result FLIPS at every level because what's a win for the AI
    is a loss from the human's node perspective, and vice versa.

    This is why the tree correctly represents each player's interests
    at their own nodes — even though we only simulate from the AI's
    perspective.
    """
    while node is not None:
        node.visits += 1
        node.wins   += result
        result       = 1.0 - result   # Flip: win for one = loss for other
        node         = node.parent


# ─────────────────────────────────────────────
# Heuristic helpers
# ─────────────────────────────────────────────

def _bfs_score(board):
    """
    Scores a non-terminal board position from the AI's perspective.

    Uses BFS shortest-path distances to goal for both players.
    The further the opponent is from their goal (relative to the AI),
    the higher the score.

    Formula:
        score = opponent_distance / (ai_distance + opponent_distance)

    This gives a value between 0 and 1:
      - Score > 0.5 → AI is closer to winning
      - Score < 0.5 → Human is closer to winning
      - Score = 0.5 → Equal distance (perfectly balanced)

    float('inf') guard: if somehow a player has no path (shouldn't
    happen in a legal game), we handle it gracefully.
    """
    ai_dist  = bfs_distance(board.pawns, board.walls, AI_PLAYER)
    opp_dist = bfs_distance(board.pawns, board.walls, HUMAN_PLAYER)

    # Guard against infinity (no path found — shouldn't happen legally)
    if ai_dist == float('inf') and opp_dist == float('inf'):
        return 0.5
    if ai_dist == float('inf'):
        return 0.0
    if opp_dist == float('inf'):
        return 1.0

    total = ai_dist + opp_dist
    if total == 0:
        return 0.5

    return opp_dist / total   # Higher opponent distance = better for AI


def _best_heuristic_move(board, player, moves):
    """
    From the list of legal moves, returns the one that results in
    the best BFS position for the current player.

    For pawn moves: pick the one that minimises YOUR distance to goal.
    For wall moves: pick the one that maximises the OPPONENT's distance.
    Mixed: evaluate all and pick the best overall delta.

    Evaluation metric per move:
        delta = your_distance_before - your_distance_after
                + opponent_distance_after - opponent_distance_before

    A positive delta means the move improved your relative position.
    The move with the highest delta is returned.

    If all moves score equally (rare), falls back to random.
    """
    opponent = HUMAN_PLAYER if player == AI_PLAYER else AI_PLAYER

    before_me  = bfs_distance(board.pawns, board.walls, player)
    before_opp = bfs_distance(board.pawns, board.walls, opponent)

    best_move  = None
    best_delta = float('-inf')

    # To keep simulation fast, only score a sample of wall moves
    pawn_moves = [m for m in moves if m[0] == "move"]
    wall_moves = [m for m in moves if m[0] == "wall"]

    # Always evaluate all pawn moves, sample up to 10 wall moves
    candidate_moves = pawn_moves + random.sample(wall_moves, min(10, len(wall_moves)))

    for move in candidate_moves:
        trial = board.clone()
        trial.apply_move(player, move)

        after_me  = bfs_distance(trial.pawns, trial.walls, player)
        after_opp = bfs_distance(trial.pawns, trial.walls, opponent)

        # How much did this move improve YOUR position?
        delta_me  = before_me  - after_me    # Positive = you got closer
        # How much did this move hurt the OPPONENT?
        delta_opp = after_opp  - before_opp  # Positive = they got further

        delta = delta_me + delta_opp

        if delta > best_delta:
            best_delta = delta
            best_move  = move

    return best_move if best_move is not None else random.choice(moves)


# ─────────────────────────────────────────────
# Main MCTS entry point
# ─────────────────────────────────────────────

class MCTS:
    """
    The public interface. api.py creates one instance of this and calls
    get_best_move(board) whenever it needs the AI to make a decision.

    Usage:
        ai = MCTS(simulations=1000)
        move = ai.get_best_move(board)
        board.apply_move(AI_PLAYER, move)
    """

    def __init__(self, simulations=SIMULATIONS):
        self.simulations = simulations

    def get_best_move(self, board):
        """
        Runs the full MCTS loop for self.simulations iterations,
        then returns the move the AI should play.

        The root node represents the current board state with the
        AI about to move.

        After all simulations, we pick the child with the MOST VISITS
        (not highest win rate). Most visits = most explored = most
        confident choice, even if a lucky branch has a higher win rate
        from fewer samples.
        """
        root = MCTSNode(board=board.clone(), player=AI_PLAYER)

        for _ in range(self.simulations):

            # 1. Selection — walk down tree to best unexplored node
            node = select(root)

            # 2. Expansion — add one new child (if not terminal)
            if not node.is_terminal():
                node = expand(node)

            # 3. Simulation — play out from new node, get result
            result = simulate(node)

            # 4. Backpropagation — update all ancestors with result
            backpropagate(node, result)

        # Return the move of the most-visited child of root
        best = root.most_visited_child()
        return best.move