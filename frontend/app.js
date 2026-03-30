const gameBoard = document.querySelector("#gameboard")
const playerDisplay = document.querySelector("#player")
const infoDisplay = document.querySelector("#info-display")
width = 17 // 9x9 board + 8x8 wall - *figre this out

const startPieces = [
    '','','','',pawn1,'','','','',
    '','','','','','','','','',
    '','','','','','','','','',
    '','','','','','','','','',
    '','','','','','','','','',
    '','','','','','','','','',
    '','','','','','','','','',
    '','','','','','','','','',
    '','','','',pawn2,'','','',''
]

function CreateBoard(){
    startPieces.forEach((startPieces, i) => {
        const blocks = document.createElement('div')
        blocks.classList.add('blocks')
        blocks.innerHTML = startPieces
        blocks.setAttribute('blocks-id', i)
        blocks.classList.add('red')
        gameBoard.append(blocks)

    })
}

CreateBoard()




const allBlocks = document.querySelectorAll("#gameboard .blocks")


console.log(allBlocks)