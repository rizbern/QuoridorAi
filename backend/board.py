boardSize = 17

def createBoard():
    return [list('.' * boardSize) for _ in range(boardSize)]

wallsRemaining = {
    'x': 10,
    'o': 10
}

board = createBoard()
copyBoard = [row[:] for row in board]

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
            row_with_coords.append((i, j, cell))

            # Pawn positions (even, even)
            if i % 2 == 0 and j % 2 == 0:
                pawn_positions.append((i, j, cell))

            # Horizontal wall anchors (odd row, even col)
            elif i % 2 != 0 and j % 2 == 0:
                if j + 2 < size:
                    horizontal_walls.append((i, j))

            # Vertical wall anchors (even row, odd col)
            elif i % 2 == 0 and j % 2 != 0:
                if i + 2 < size:
                    vertical_walls.append((i, j))

        board_with_coords.append(row_with_coords)

    return {
        "board": board_with_coords,
        "pawns": pawn_positions,
        "horizontal_walls": horizontal_walls,
        "vertical_walls": vertical_walls
    }

def getBoardState():
    return [row[:] for row in copyBoard]

def placeWall(player, anchor, orientation):
    i, j = anchor

    # check wall count
    if wallsRemaining[player] <= 0:
        return None

    if not isValidWallPlacement(i, j, orientation):
        return None

    if orientation == "H":
        copyBoard[i][j] = '-'
        copyBoard[i][j+1] = '-'
        copyBoard[i][j+2] = '-'

    elif orientation == "V":
        copyBoard[i][j] = '|'
        copyBoard[i+1][j] = '|'
        copyBoard[i+2][j] = '|'

    wallsRemaining[player] -= 1
    return copyBoard

def isValidWallPlacement(i, j, orientation):
    size = boardSize

    if orientation == "H":
        # odd row, even col
        if not (i % 2 != 0 and j % 2 == 0):
            print("Wrong orientation")
            return False

        if j + 2 >= size:
            print("Out of bound friend")
            return False

        # overlap check
        if copyBoard[i][j] != '.' or copyBoard[i][j+1] != '.' or copyBoard[i][j+2] != '.':
            print("Can't overlap mate")
            return False
        
        if copyBoard[i-1][j+1] == '|' or copyBoard[i+1][j+1] == '|':
            return False

    elif orientation == "V":
        # even row, odd col
        if not (i % 2 == 0 and j % 2 != 0):
            print("Wrong orientation")
            return False

        if i + 2 >= size:
            print("Out of bound friend")
            return False

        # overlap check
        if copyBoard[i][j] != '.' or copyBoard[i+1][j] != '.' or copyBoard[i+2][j] != '.':
            print("Can't overlap mate")
            return False
        
        # if you try to 
        if copyBoard[i+1][j-1] == '-' or copyBoard[i+1][j+1] == '-':
            return False
        
    else:
        return False
        

    return True

def placeWall(player, anchor, orientation):
    i, j = anchor

    if not isValidWallPlacement(i, j, orientation):
        return None

    if orientation == "H":
        copyBoard[i][j] = '-'
        copyBoard[i][j+1] = '-'
        copyBoard[i][j+2] = '-'

    elif orientation == "V":
        copyBoard[i][j] = '|'
        copyBoard[i+1][j] = '|'
        copyBoard[i+2][j] = '|'

    return copyBoard

def findPawn(player):
    for i in range(boardSize):
        for j in range(boardSize):
            if copyBoard[i][j] == player:
                return (i, j)
    return None

def movePawn(player, direction):
    opponent = 'o' if player == 'x' else 'x'

    i, j = findPawn(player)

    if direction == "DOWN":
        ni, nj = i + 2, j

        # check opponent in front
        if copyBoard[i+2][j] == opponent:
            ni = i + 4  # jump

        if ni < boardSize:
            copyBoard[i][j] = '.'
            copyBoard[ni][nj] = player

    elif direction == "UP":
        ni, nj = i - 2, j

        if copyBoard[i-2][j] == opponent:
            ni = i - 4

        if ni >= 0:
            copyBoard[i][j] = '.'
            copyBoard[ni][nj] = player

    elif direction == "RIGHT":
        ni, nj = i, j + 2

        if copyBoard[i][j+2] == opponent:
            nj = j + 4

        if nj < boardSize:
            copyBoard[i][j] = '.'
            copyBoard[ni][nj] = player

    elif direction == "LEFT":
        ni, nj = i, j - 2

        if copyBoard[i][j-2] == opponent:
            nj = j - 4

        if nj >= 0:
            copyBoard[i][j] = '.'
            copyBoard[ni][nj] = player

    return copyBoard


# placePawn('x', (0,0))
# placePawn('o', (2,2))
# placeWall('x', (1,0), "H")  
# # fills: (1,0), (1,1), (1,2)

# placeWall('o', (0,1), "V")
# # fills: (0,1), (1,1), (2,1)
# print(copyBoard)


