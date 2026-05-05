import math
import random
from board import (
    getLegalMoves, movePawn, placeWall,
    bfsDistance, OPPONENT, _applyWall,
    _isValidWallFast, findPawn, GOAL_ROW,
    BOARD_SIZE, isValidWallPlacement
)

ITERATIONS   = 1000
C            = 1.41
AI_PLAYER    = 'o'
HUMAN_PLAYER = 'x'


# ─────────────────────────────────────────────
# MCTSNode
# ─────────────────────────────────────────────

class MCTSNode:
    def __init__(self, state, parent=None, move=None, good_walls=None):
        self.state    = state
        self.parent   = parent
        self.move     = move
        self.children = []
        self.visits   = 0
        self.score    = 0.0

        all_moves  = getLegalMoves(state, state['current_player'], fast=True)
        pawn_moves = [m for m in all_moves if m['type'] == 'pawn']
        wall_moves = [m for m in all_moves if m['type'] == 'wall']

        # Root AI node: use pre-filtered good walls passed in from get_ai_move
        # good_walls=[]  → no wall passes opp_slowdown>=2, pawn moves only
        # good_walls=None → child node, use fast proximity sort
        if parent is None and state['current_player'] == AI_PLAYER:
            wall_moves = good_walls if good_walls else []
        else:
            human_pos  = findPawn(state['board'], HUMAN_PLAYER)
            human_goal = GOAL_ROW[HUMAN_PLAYER]
            if human_pos:
                hr, hc = human_pos
                wall_moves.sort(key=lambda m: (
                    abs(m['anchor'][0] - human_goal) + abs(m['anchor'][1] - hc) * 0.5
                ))
            else:
                random.shuffle(wall_moves)
            # Cap at 6 walls for child nodes — keeps tree from going too wide
            wall_moves = wall_moves[:6]

        self.untried_moves = pawn_moves + wall_moves

    def is_fully_expanded(self):
        return len(self.untried_moves) == 0

    def ucb1(self):
        if self.visits == 0:
            return float('inf')
        exploitation = self.score / self.visits
        exploration  = C * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration


# ─────────────────────────────────────────────
# select
# ─────────────────────────────────────────────

def select(node):
    while node.is_fully_expanded() and node.children:
        node = max(node.children, key=lambda n: n.ucb1())
    return node


# ─────────────────────────────────────────────
# expand
# ─────────────────────────────────────────────

def expand(node):
    move = node.untried_moves.pop(random.randrange(len(node.untried_moves)))

    if move['type'] == 'pawn':
        r, c      = move['target']
        new_state = movePawn(node.state, node.state['current_player'], r, c)
    else:
        new_state = placeWall(node.state, node.state['current_player'],
                              move['anchor'], move['orientation'])

    if new_state is None:
        return node

    child = MCTSNode(new_state, parent=node, move=move)
    node.children.append(child)
    return child


# ─────────────────────────────────────────────
# simulate
# ─────────────────────────────────────────────

def simulate(node, last_ai_pos=None):
    state = node.state
    if state['winner'] == AI_PLAYER:    return 1.0
    if state['winner'] == HUMAN_PLAYER: return 0.0
    return evaluate(state, last_ai_pos=last_ai_pos)


def evaluate(state, last_ai_pos=None):
    board   = state['board']
    d_ai    = bfsDistance(board, AI_PLAYER)
    d_human = bfsDistance(board, HUMAN_PLAYER)

    if d_ai    is None: return 0.0
    if d_human is None: return 1.0
    if d_ai    == 0:    return 1.0
    if d_human == 0:    return 0.0

    # Immediate win/loss
    if d_ai    == 1: return 0.95
    if d_human == 1: return 0.05

    w = state['walls_remaining']

    # 1. Path difference (dataset: dist_advantage_before)
    path_diff = d_human - d_ai

    # 2. Raw board progress
    ai_pos    = findPawn(board, AI_PLAYER)
    human_pos = findPawn(board, HUMAN_PLAYER)
    ai_row    = ai_pos[0]    if ai_pos    else 16
    human_row = human_pos[0] if human_pos else 0
    ai_progress    = (16 - ai_row) / 16
    human_progress = human_row / 16
    progress_diff  = ai_progress - human_progress

    # 3. Anti-oscillation: penalise if AI returned to its previous position
    oscillation_penalty = 0.0
    if last_ai_pos and ai_pos and ai_pos == last_ai_pos:
        oscillation_penalty = -1.5

    # 4. Wall advantage — only relevant when not losing
    wall_diff   = w[AI_PLAYER] - w[HUMAN_PLAYER]
    wall_weight = 0.4 if path_diff >= 0 else 0.1

    # 5. Game phase for sigmoid sharpness
    game_phase = (ai_progress + human_progress) / 2

    score = (
        2.0 * path_diff          +
        1.0 * progress_diff      +
        wall_weight * wall_diff  +
        oscillation_penalty
    )

    sharpness = 0.8 + 0.5 * game_phase
    return 1 / (1 + math.exp(-sharpness * score))


# ─────────────────────────────────────────────
# backpropagate
# ─────────────────────────────────────────────

def backpropagate(node, score):
    while node is not None:
        node.visits += 1
        if node.state['current_player'] == AI_PLAYER:
            node.score += score
        else:
            node.score += (1 - score)
        node = node.parent


# ─────────────────────────────────────────────
# best_child
# ─────────────────────────────────────────────

def best_child(root):
    return max(root.children, key=lambda n: n.visits)


# ─────────────────────────────────────────────
# mcts
# ─────────────────────────────────────────────

def mcts(state, good_walls=None, last_ai_pos=None, iterations=ITERATIONS):
    root = MCTSNode(state, good_walls=good_walls)

    for _ in range(iterations):
        node = select(root)
        if node.untried_moves and node.state['winner'] is None:
            node = expand(node)
        score = simulate(node, last_ai_pos=last_ai_pos)
        backpropagate(node, score)

    return best_child(root)


# ─────────────────────────────────────────────
# Wall pre-filter — runs once per AI turn
# Dataset insight: opp_slowdown >= 2 is the threshold for a good wall
# Walls that add only 0-1 steps to opponent are labelled bad in dataset
# ─────────────────────────────────────────────

def _prefilter_walls(state):
    board      = state['board']
    wr         = state['walls_remaining']
    human_goal = GOAL_ROW[HUMAN_PLAYER]
    human_pos  = findPawn(board, HUMAN_PLAYER)

    if wr[AI_PLAYER] <= 0:
        return []

    d_ai_base    = bfsDistance(board, AI_PLAYER)    or 99
    d_human_base = bfsDistance(board, HUMAN_PLAYER) or 99

    # All fast-valid walls sorted toward human goal
    walls = []
    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            for ori in ('H', 'V'):
                if _isValidWallFast(board, wr, AI_PLAYER, (i, j), ori):
                    walls.append({'type': 'wall', 'anchor': (i, j), 'orientation': ori})

    if human_pos:
        hr, hc = human_pos
        walls.sort(key=lambda m: (
            abs(m['anchor'][0] - human_goal) + abs(m['anchor'][1] - hc) * 0.5
        ))

    # Adaptive threshold based on urgency:
    # Dataset shows opp_slowdown>=2 is ideal, but when human is 1-2 steps
    # from winning, even a +1 slowdown is critical — better than nothing.
    threshold = 2 if d_human_base > 2 else 1

    good = []
    for m in walls[:30]:
        test = [row[:] for row in board]
        _applyWall(test, m['anchor'], m['orientation'])
        d_ai_new    = bfsDistance(test, AI_PLAYER)    or 99
        d_human_new = bfsDistance(test, HUMAN_PLAYER) or 99
        opp_slowdown = d_human_new - d_human_base
        ai_slowdown  = d_ai_new  - d_ai_base
        net = opp_slowdown - ai_slowdown
        if opp_slowdown >= threshold and net >= 0:
            good.append((net, opp_slowdown, m))

    good.sort(key=lambda x: (-x[0], -x[1]))
    return [m for _, _, m in good]


# ─────────────────────────────────────────────
# get_ai_move — entry point
# ─────────────────────────────────────────────

def get_ai_move(state, last_ai_pos=None):
    good_walls = _prefilter_walls(state)
    best = mcts(state, good_walls=good_walls, last_ai_pos=last_ai_pos)
    move = best.move

    # Hard block: if MCTS picked a move that returns AI to its last position,
    # override it with the next best child that doesn't oscillate
    if (last_ai_pos and move and move['type'] == 'pawn'):
        r, c = move['target']
        if (r, c) == last_ai_pos:
            # Find next most visited child that isn't going back
            root_children = sorted(
                best.parent.children if best.parent else [],
                key=lambda n: n.visits, reverse=True
            )
            for child in root_children:
                if child.move and child.move['type'] == 'pawn':
                    cr, cc = child.move['target']
                    if (cr, cc) != last_ai_pos:
                        move = child.move
                        break
                elif child.move and child.move['type'] == 'wall':
                    move = child.move
                    break

    # Final full BFS validation on chosen wall
    if move and move['type'] == 'wall':
        valid, _ = isValidWallPlacement(
            state['board'], state['walls_remaining'],
            AI_PLAYER, move['anchor'], move['orientation']
        )
        if not valid:
            all_moves  = getLegalMoves(state, AI_PLAYER, fast=False)
            pawn_moves = [m for m in all_moves if m['type'] == 'pawn']
            move       = pawn_moves[0] if pawn_moves else None

    return move


# ─────────────────────────────────────────────
# Smoke test
# ─────────────────────────────────────────────

if __name__ == '__main__':
    import time
    from board import initGame

    print("=== Game start (both at center, no good walls) ===")
    state = initGame()
    walls = _prefilter_walls(state)
    print(f"Good walls: {len(walls)}")
    t = time.time()
    move = get_ai_move(state)
    print(f"AI chose: {move}  ({time.time()-t:.2f}s)")

    print("\n=== AI far behind (X at row 3, should run) ===")
    state2 = initGame()
    state2['board'][0][8] = '.'
    state2['board'][6][8] = 'x'
    state2['current_player'] = 'o'
    walls2 = _prefilter_walls(state2)
    print(f"Good walls: {len(walls2)}")
    t = time.time()
    move2 = get_ai_move(state2)
    print(f"AI chose: {move2}  ({time.time()-t:.2f}s)  <- should be pawn")

    print("\n=== X close to goal, AI should block ===")
    state3 = initGame()
    state3['board'][0][8]  = '.'
    state3['board'][16][8] = '.'
    state3['board'][14][8] = 'x'   # human 1 step from goal
    state3['board'][8][8]  = 'o'
    state3['walls_remaining'] = {'x': 8, 'o': 6}
    state3['current_player'] = 'o'
    walls3 = _prefilter_walls(state3)
    print(f"Good walls: {len(walls3)}")
    for w in walls3[:3]: print(f"  {w}")
    t = time.time()
    move3 = get_ai_move(state3)
    print(f"AI chose: {move3}  ({time.time()-t:.2f}s)  <- should be blocking wall")