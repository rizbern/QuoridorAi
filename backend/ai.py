import math
import random
from copy import deepcopy

from board import (
    getLegalMoves, movePawn, placeWall,
    bfsDistance, findPawn, OPPONENT
)

ITERATIONS   = 200   # how many MCTS iterations per move
C            = 1.41   # exploration constant
AI_PLAYER    = 'o'
HUMAN_PLAYER = 'x'

class MCTSNode:
    def __init__(self, state, parent=None, move=None):
        self.state         = state
        self.parent        = parent
        self.move          = move          # move that led HERE from parent
        self.children      = []
        self.visits        = 0
        self.score         = 0.0
        self.untried_moves = getLegalMoves(state, state['current_player'])

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def ucb1(self):
        if self.visits == 0:
            return float('inf')
        exploitation = self.score / self.visits
        exploration  = C * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration

def select(node):
    while node.is_fully_expanded() and node.children:
        node = max(node.children, key=lambda n: n.ucb1())
    return node

def expand(node):
    move = node.untried_moves.pop(random.randrange(len(node.untried_moves)))

    if move['type'] == 'pawn':
        r, c      = move['target']
        new_state = movePawn(node.state, node.state['current_player'], r, c)
    else:
        new_state = placeWall(node.state, node.state['current_player'],
                              move['anchor'], move['orientation'])

    if new_state is None:
        return node   # fallback: illegal move slipped through, stay at node

    child = MCTSNode(new_state, parent=node, move=move)
    node.children.append(child)
    return child

def simulate(node):
    state = node.state

    # Terminal state — certain result
    if state['winner'] == AI_PLAYER:
        return 1.0
    if state['winner'] == HUMAN_PLAYER:
        return 0.0

    return evaluate(state)

def evaluate(state):
    """
    need bfs heuristics here
    """
    d_ai    = bfsDistance(state['board'], AI_PLAYER)
    d_human = bfsDistance(state['board'], HUMAN_PLAYER)

    if d_ai    is None: return 0.0   # AI is trapped = loss
    if d_human is None: return 1.0   # human is trapped = win

    return d_human / (d_ai + d_human)

def backpropagate(node, score):
    while node is not None:
        node.visits += 1
        node.score  += score
        node = node.parent

def best_child(root):
    return max(root.children, key=lambda n: n.visits)

def mcts(state, iterations=ITERATIONS):
    root = MCTSNode(state)

    for _ in range(iterations):
        # 1. select
        node = select(root)

        # 2. expand (if not terminal and has untried moves)
        if node.untried_moves and state['winner'] is None:
            node = expand(node)

        # 3. simulate
        score = simulate(node)

        # 4. backpropagate
        backpropagate(node, score)

    return best_child(root)

def get_ai_move(state):
    """
    Given the current game state, return the best move for the AI
    as a dict:
      {'type': 'pawn', 'target': (row, col)}
      {'type': 'wall', 'anchor': (i,j), 'orientation': 'H'|'V'}
    """
    best = mcts(state)
    return best.move

if __name__ == '__main__':
    from board import initGame

    state = initGame()
    print("Board ready. AI is thinking...")

    move = get_ai_move(state)
    print(f"AI chose: {move}")