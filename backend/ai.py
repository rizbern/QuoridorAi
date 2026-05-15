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


class MCTSNode:
    def __init__(self, state, parent=None, move=None):
        self.state         = state
        self.parent        = parent
        self.move          = move
        self.children      = []
        self.wins          = 0
        self.visits        = 0
        self.untried_moves = None

    def is_fully_expanded(self):
        if self.untried_moves is None:
            return False
        return len(self.untried_moves) == 0

    def ucb1(self):
        if self.visits == 0:
            return float('inf')
        exploitation = self.wins / self.visits
        exploration  = C * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration

    def find_child_by_state(self, target_state):
        target_board = target_state['board']
        target_pawns = (findPawn(target_board, 'x'), findPawn(target_board, 'o'))
        target_cp    = target_state['current_player']
        for child in self.children:
            cb     = child.state['board']
            cpawns = (findPawn(cb, 'x'), findPawn(cb, 'o'))
            if cpawns == target_pawns and child.state['current_player'] == target_cp:
                return child
        return None


def select(node):
    while node.is_fully_expanded() and node.children:
        node = max(node.children, key=lambda n: n.ucb1())
    return node


def expand(node, good_walls=None):
    if node.untried_moves is None:
        all_moves  = getLegalMoves(node.state, node.state['current_player'], fast=True)
        pawn_moves = [m for m in all_moves if m['type'] == 'pawn']
        wall_moves = [m for m in all_moves if m['type'] == 'wall']
        if node.parent is None and node.state['current_player'] == AI_PLAYER:
            wall_moves = good_walls if good_walls else []
        else:
            human_pos  = findPawn(node.state['board'], HUMAN_PLAYER)
            human_goal = GOAL_ROW[HUMAN_PLAYER]
            if human_pos:
                hr, hc = human_pos
                wall_moves.sort(key=lambda m: (
                    abs(m['anchor'][0] - human_goal) + abs(m['anchor'][1] - hc) * 0.5
                ))
            else:
                random.shuffle(wall_moves)
            wall_moves = wall_moves[:6]
        node.untried_moves = pawn_moves + wall_moves
    if not node.untried_moves:
        return node
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


def simulate(node, last_ai_pos=None):
    state = node.state
    if state['winner'] == AI_PLAYER:    return 1
    if state['winner'] == HUMAN_PLAYER: return 0
    d_ai    = bfsDistance(state['board'], AI_PLAYER)
    d_human = bfsDistance(state['board'], HUMAN_PLAYER)
    if d_ai    is None: return 0
    if d_human is None: return 1
    if d_ai <= 2 or d_human <= 2:
        return _rollout(state)
    return evaluate(state, last_ai_pos=last_ai_pos)


def _rollout(state, max_moves=10):
    from copy import deepcopy
    cur = deepcopy(state)
    for _ in range(max_moves):
        if cur['winner']:
            break
        moves = getLegalMoves(cur, cur['current_player'], fast=True)
        if not moves:
            break
        m = random.choice(moves[:8])
        if m['type'] == 'pawn':
            r, c = m['target']
            ns   = movePawn(cur, cur['current_player'], r, c)
        else:
            ns = placeWall(cur, cur['current_player'], m['anchor'], m['orientation'])
        if ns:
            cur = ns
    if cur['winner'] == AI_PLAYER:    return 1
    if cur['winner'] == HUMAN_PLAYER: return 0
    return evaluate(cur)


def evaluate(state, last_ai_pos=None):
    board   = state['board']
    d_ai    = bfsDistance(board, AI_PLAYER)
    d_human = bfsDistance(board, HUMAN_PLAYER)
    if d_ai    is None: return 0.0
    if d_human is None: return 1.0
    if d_ai    == 0:    return 1.0
    if d_human == 0:    return 0.0
    if d_ai    == 1:    return 0.95
    if d_human == 1:    return 0.05
    w = state['walls_remaining']
    path_diff  = d_human - d_ai
    ai_pos     = findPawn(board, AI_PLAYER)
    human_pos  = findPawn(board, HUMAN_PLAYER)
    ai_row     = ai_pos[0]    if ai_pos    else 16
    human_row  = human_pos[0] if human_pos else 0
    ai_progress    = (16 - ai_row) / 16
    human_progress = human_row / 16
    progress_diff  = ai_progress - human_progress
    oscillation_penalty = -1.5 if (last_ai_pos and ai_pos and ai_pos == last_ai_pos) else 0.0
    wall_diff   = w[AI_PLAYER] - w[HUMAN_PLAYER]
    wall_weight = 0.4 if path_diff >= 0 else 0.1
    game_phase  = (ai_progress + human_progress) / 2
    score = (
        2.0 * path_diff         +
        1.0 * progress_diff     +
        wall_weight * wall_diff +
        oscillation_penalty
    )
    sharpness = 0.8 + 0.5 * game_phase
    return 1 / (1 + math.exp(-sharpness * score))


def backpropagate(node, result):
    while node is not None:
        node.visits += 1
        if node.state['current_player'] == AI_PLAYER:
            node.wins += 1 if result < 0.5 else 0
        else:
            node.wins += 1 if result > 0.5 else 0
        node = node.parent


def best_child(root):
    return max(root.children, key=lambda n: n.visits)


_root_cache = None


def mcts(state, good_walls=None, last_ai_pos=None, iterations=ITERATIONS):
    global _root_cache
    root = None
    if _root_cache is not None:
        root = _root_cache.find_child_by_state(state)
        if root is not None:
            root.parent = None
    if root is None:
        root = MCTSNode(state)
    for _ in range(iterations):
        node = select(root)
        if not node.is_fully_expanded() and node.state['winner'] is None:
            node = expand(node, good_walls=good_walls if node.parent is None else None)
        result = simulate(node, last_ai_pos=last_ai_pos)
        backpropagate(node, result)
    _root_cache = root
    return best_child(root)


def _prefilter_walls(state):
    board      = state['board']
    wr         = state['walls_remaining']
    human_goal = GOAL_ROW[HUMAN_PLAYER]
    human_pos  = findPawn(board, HUMAN_PLAYER)
    if wr[AI_PLAYER] <= 0:
        return []
    d_ai_base    = bfsDistance(board, AI_PLAYER)    or 99
    d_human_base = bfsDistance(board, HUMAN_PLAYER) or 99
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
    threshold = 2 if d_human_base > 2 else 1
    good = []
    for m in walls[:30]:
        test = [row[:] for row in board]
        _applyWall(test, m['anchor'], m['orientation'])
        d_ai_new     = bfsDistance(test, AI_PLAYER)    or 99
        d_human_new  = bfsDistance(test, HUMAN_PLAYER) or 99
        opp_slowdown = d_human_new - d_human_base
        ai_slowdown  = d_ai_new  - d_ai_base
        net          = opp_slowdown - ai_slowdown
        if opp_slowdown >= threshold and net >= 0:
            good.append((net, opp_slowdown, m))
    good.sort(key=lambda x: (-x[0], -x[1]))
    return [m for _, _, m in good]


def get_ai_move(state, last_ai_pos=None):
    good_walls = _prefilter_walls(state)
    best       = mcts(state, good_walls=good_walls, last_ai_pos=last_ai_pos)
    move       = best.move
    if last_ai_pos and move and move['type'] == 'pawn':
        r, c = move['target']
        if (r, c) == last_ai_pos:
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