import random 
import ast # list to text and back
from mcts import numberOfSimulation

aiPlayer = 'o'
boardSize = 17
numberOfSimulation = numberOfSimulation

board = [
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................'),
    list('.................')
]

startingPlayer = 'x'
currentPlayer = startingPlayer

def getGameState(board):
    board_with_coords = []
    pawn_positions = []
    horizontal_walls = []
    vertical_walls = []

    size = len(board)

    for i in range(size):
        row_with_coords = []

        for j in range(size):
            cell = board[i][j]

            # attach coordinates
            row_with_coords.append((i, j, cell))

            # Pawn positions (playable cells)
            if i % 2 != 0 and j % 2 != 0:
                pawn_positions.append((i, j, cell))

            # Horizontal walls (store as 2-edge structure)
            elif i % 2 == 0 and j % 2 != 0:
                if j + 2 < size:
                    horizontal_walls.append((
                        (i, j),       # first segment
                        (i, j + 2)    # second segment (2,3   2,4   2,5) <- 3 to 5 block horizontal
                    ))

            # Vertical walls (store as 2-edge structure)
            elif i % 2 != 0 and j % 2 == 0:
                if i + 2 < size:
                    vertical_walls.append((
                        (i, j),       # first segment
                        (i + 2, j)    # second segment (3,2  4,2  5,2) <- 3 to 5 block verticle
                    ))

        board_with_coords.append(row_with_coords)

    return {
        "board": board_with_coords,
        "pawns": pawn_positions,
        "horizontal_walls": horizontal_walls,
        "vertical_walls": vertical_walls
    }

# (0,0) ─ (0,1) ─ (0,2)
#   |       |       |
# (1,0)   (1,1)   (1,2)             (1,1) -> pawn
#   |       |       |
# (2,0) ─ (2,1) ─ (2,2)

# gameState = getGameState(board)
# print(f"pawns:  {gameState["pawns"]}")
# print(f"walls:  {gameState["walls"]}")


# tasK 1 -> able to place pawns in its correct position
# task 2 -> able to place walls in its correct postion