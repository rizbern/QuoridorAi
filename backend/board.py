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

copyBoard = board

startingPlayer = 'x'
currentPlayer = startingPlayer

def initializeBoard(board):
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

            # Pawn positions (now EVEN indices)
            if i % 2 == 0 and j % 2 == 0:
                pawn_positions.append((i, j, cell))

            # Horizontal walls (odd row, even column)
            elif i % 2 != 0 and j % 2 == 0:
                if j + 1 < size:  # wall between (i, j) and (i, j+1)
                    horizontal_walls.append((
                        (i, j),
                        (i, j + 1)
                    ))

            # Vertical walls (even row, odd column)
            elif i % 2 == 0 and j % 2 != 0:
                if i + 1 < size:  # wall between (i, j) and (i+1, j)
                    vertical_walls.append((
                        (i, j),
                        (i + 1, j)
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

initGameState = initializeBoard(copyBoard)
# print(f"pawns:  {initGameState["pawns"]}") #(even)
# print(f"Board:  {gameState["board"]}")
# print(f"horizontal_walls:  {gameState["horizontal_walls"]}") (odd)
# print(f"vertical_walls:  {gameState["vertical_walls"]}") (odd)

def getBoardState():
    # get copy of the board
    return [row[:] for row in copyBoard]


# tasK 1 -> able to place pawns in its correct position
# pawns at even positions

def placePawn(currentPlayer, pos):
    currentBoard = getBoardState()
    # pos -> (i,j)
    i,j = pos
    if i % 2 == 0 and j % 2 == 0:
        copyBoard[i][j] = currentPlayer
        return copyBoard
    else:
        print("Cant place a pawn there mate")
        return currentBoard



#TEST placePawn
# startingPlayer ="x" , aiPlayer = "o" - this will be flipped based on the players turns or ai turn
# temp = placePawn(aiPlayer,(0,0)) # this is basically the position of the pawn that the pplyer is gona choose.
# print(temp)
# temp = placePawn((0,1))
# print(temp)
# temp = placePawn((2,0))
# print(temp)


# task 2 -> able to place walls in its correct postion


print(f"horizontal_walls:  {initGameState["horizontal_walls"]}")
print(f"vertical_walls:  {initGameState["vertical_walls"]}")

def placeWall(cuurentPlayer, pos):
    i, j, k, l,m, n = pos
    if i % 2 != 0:
        # player can place a horizontal wall
        # place wall from i -> j and j-> k
        copyBoard[i][j], copyBoard[k][l], copyBoard[m][n] = "-", "-", "-"
        return copyBoard
# test
temp = placeWall(startingPlayer, (1,0,1,1,1,2))  # (start, mid, end)
print(temp)