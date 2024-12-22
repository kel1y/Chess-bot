# first let's make sure you have internet enabled
import requests
requests.get('http://www.google.com',timeout=10).ok

%%capture
# ensure we are on the latest version of kaggle-environments
!pip install --upgrade kaggle-environments

# Now let's set up the chess environment!
from kaggle_environments import make
env = make("chess", debug=True)

# this should run a game in the environment between two random bots
# NOTE: each game starts from a randomly selected opening
result = env.run(["random", "random"])
env.render(mode="ipython", width=1000, height=1000) 

%%writefile main.py
from Chessnut import Game
import random

def fen_to_board_array(fen):
    """Convert a FEN string to a flat list representing the chessboard."""
    board = []
    for row in fen.split()[0].split('/'):
        for char in row:
            if char.isdigit():
                board.extend([" "] * int(char))
            else:
                board.append(char)
    return board

def quick_evaluate(board_fen):
    """Lightweight board evaluation to score material advantage."""
    values = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 100,
              "p": -1, "n": -3, "b": -3, "r": -5, "q": -9, "k": -100}
    board = fen_to_board_array(board_fen)
    return sum(values.get(piece, 0) for piece in board)

def king_trap_score(board_array, king_pos):
    """Estimate king trapping potential by counting surrounding pieces."""
    trapping_score = 0
    x, y = divmod(king_pos, 8)
    directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if 0 <= nx < 8 and 0 <= ny < 8:
            pos = nx * 8 + ny
            if board_array[pos] in "PNBRQK":
                trapping_score += 1

    return trapping_score

def prioritize_moves(moves, obs_board, opponent_king_pos):
    """Categorize and prioritize moves based on strategy."""
    checkmate_moves = []
    capture_moves = []
    king_trap_moves = []
    strategic_moves = []

    board_array = fen_to_board_array(obs_board)

    for move in moves:
        # Apply move
        board = Game(obs_board)
        board.apply_move(move)

        # Checkmate detection
        if board.status == Game.CHECKMATE:
            checkmate_moves.append(move)
            continue

        # Capture moves
        target_square = Game.xy2i(move[2:4])
        if board_array[target_square] not in " ":
            capture_moves.append(move)
            continue

        # King trapping moves
        if opponent_king_pos is not None:
            trap_score = king_trap_score(board_array, opponent_king_pos)
            if trap_score > 0:
                king_trap_moves.append((move, trap_score))
                continue

        # Strategic moves
        score = quick_evaluate(board.get_fen())
        strategic_moves.append((move, score))

    return checkmate_moves, capture_moves, king_trap_moves, strategic_moves

def chess_bot(obs):
    """Optimized chess bot to reduce timeouts and maintain intelligence."""
    game = Game(obs.board)
    moves = list(game.get_moves())
    if not moves:
        return "0000"  # No legal moves

    # Locate the opponent's king
    opponent_king_pos = None
    board_array = fen_to_board_array(obs.board)
    for i, piece in enumerate(board_array):
        if piece == 'k':  # Opponent's king
            opponent_king_pos = i
            break

    # Prioritize moves
    checkmate_moves, capture_moves, king_trap_moves, strategic_moves = prioritize_moves(
        moves, obs.board, opponent_king_pos
    )

    # Decide the best move
    if checkmate_moves:
        return random.choice(checkmate_moves)
    if capture_moves:
        return random.choice(capture_moves)
    if king_trap_moves:
        return max(king_trap_moves, key=lambda x: x[1])[0]
    if strategic_moves:
        return max(strategic_moves, key=lambda x: x[1])[0]

    # Default fallback
    return random.choice(moves)


result = env.run(["main.py", "random"])
print("Agent exit status/reward/time left: ")
# look at the generated replay.json and print out the agent info
for agent in result[-1]:
    print("\t", agent.status, "/", agent.reward, "/", agent.observation.remainingOverageTime)
print("\n")
# render the game
env.render(mode="ipython", width=1000, height=1000) 
