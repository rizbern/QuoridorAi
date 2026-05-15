![alt text](/assets/quoridorAI.png)


I have used BFS with heuristics to find the best path which is later passed on to MCTS for random rollouts and finding the best possible moves.
Without BFS with heuristics, MCTS plays random moves. 

![alt text](https://media.geeksforgeeks.org/wp-content/uploads/20251108150801887143/repeated_x_times.webp)


To fix the problem of existing path, I use BFS to find a possible path to the terminal node.
If there's no path, you cannot place a wall.

TO run in terminal use:

cd backend \n
python game.py

Check the full frontend implementation at https://rizbernpy.pythonanywhere.com/

To run the frontend locally use:
python run.py

checkout my linkedin https://in.linkedin.com/in/risbern-passanha-88174a2b0
