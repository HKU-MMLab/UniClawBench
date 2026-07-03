import os
import sys
import time
from pathlib import Path

# random-25x25: 25x25, 338 filled cells, unique solution verified offline.
PUZZLE = {
    "name": "random-25x25",
    "label": "25x25",
    "solution": [
        "0011111110011000010101111",
        "1101010100010011001001011",
        "0111100110111110000010001",
        "1001001111101000001010001",
        "1011011111001110111011000",
        "1110110001010000100111111",
        "0100111101110111010000000",
        "1100000100110111000110111",
        "1110111001011001000010100",
        "0001100111000101110111000",
        "1001100101110101000011000",
        "0001101011111111100101100",
        "1010100110111101001001110",
        "0101011110000110110101101",
        "1100110110111000011100110",
        "1110001011101111101001110",
        "0001111111100011001111011",
        "0010111110011011111110010",
        "1110100000100101100111111",
        "1111111101100011010101001",
        "0101110100010001001001010",
        "1110111111100000101011001",
        "0100011110100110010110010",
        "1010110001110011100011111",
        "1000110001100011100001100",
    ],
    "row_clues": [[7, 2, 1, 1, 4], [2, 1, 1, 1, 1, 2, 1, 1, 2], [4, 2, 5, 1, 1], [1, 1, 5, 1, 1, 1, 1], [1, 2, 5, 3, 3, 2], [3, 2, 1, 1, 1, 6], [1, 4, 3, 3, 1], [2, 1, 2, 3, 2, 3], [3, 3, 1, 2, 1, 1, 1], [2, 3, 1, 3, 3], [1, 2, 1, 3, 1, 1, 2], [2, 1, 9, 1, 2], [1, 1, 1, 2, 4, 1, 1, 3], [1, 1, 4, 2, 2, 1, 2, 1], [2, 2, 2, 3, 3, 2], [3, 1, 3, 5, 1, 3], [8, 2, 4, 2], [1, 5, 2, 7, 1], [3, 1, 1, 1, 2, 6], [8, 2, 2, 1, 1, 1, 1], [1, 3, 1, 1, 1, 1, 1, 1], [3, 7, 1, 1, 2, 1], [1, 4, 1, 2, 1, 2, 1], [1, 1, 2, 3, 3, 5], [1, 2, 2, 3, 2]],
    "col_clues": [[1, 3, 2, 1, 1, 2, 2, 1, 2], [2, 4, 3, 5], [1, 1, 2, 1, 1, 1, 3, 1, 1], [5, 3, 1, 1, 2], [1, 1, 2, 5, 1, 6, 2], [2, 3, 1, 2, 2, 6], [1, 2, 1, 1, 1, 1, 3, 1, 2], [5, 2, 2, 3, 2, 4], [1, 3, 1, 7, 2], [4, 4, 2, 1, 1, 2], [2, 2, 3, 3, 2, 4], [3, 4, 3, 1, 1, 1, 1], [1, 3, 1, 2, 2, 1], [1, 1, 2, 5, 1, 1, 1], [2, 1, 2, 1, 1, 3, 1, 3], [1, 7, 6, 2], [2, 1, 1, 1, 1, 2, 1, 2], [1, 1, 1, 1, 2, 1, 1, 1], [1, 2, 1, 4, 2], [1, 1, 1, 1, 1, 2, 4, 1], [4, 4, 3, 3], [2, 2, 5, 2, 4, 2], [1, 1, 2, 5, 1, 2], [2, 1, 1, 1, 5, 1, 2], [4, 1, 1, 1, 1, 2, 1, 1]],
}

N = 25


class Nonogram:
    def __init__(self, state_file=None):
        default_state_file = Path(__file__).resolve().parent / "nonogram_board.txt"
        self.state_file = Path(state_file) if state_file else default_state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.duration_file = Path(os.environ["NONOGRAM_DURATION_PATH"]) if os.environ.get("NONOGRAM_DURATION_PATH") else None
        self.attempt = os.environ.get("NONOGRAM_ATTEMPT", "1")
        self.game_start_unix = time.time()
        self.first_move_unix = None
        self.last_move_unix = None

        self.puzzle = PUZZLE
        self.solution = [[int(v) for v in row] for row in PUZZLE["solution"]]
        self.row_clues = PUZZLE["row_clues"]
        self.col_clues = PUZZLE["col_clues"]
        # cell states: 0 = unknown/blank, 1 = filled, 2 = marked-empty (X)
        self.board = [[0 for _ in range(N)] for _ in range(N)]
        self.total_filled = sum(v for row in self.solution for v in row)
        self.game_over = False
        self.write_duration_file("NOT_STARTED")
        self.write_state_file()

    def mark_valid_move(self):
        now = time.time()
        if self.first_move_unix is None:
            self.first_move_unix = now
        self.last_move_unix = now
        self.write_duration_file("IN_PROGRESS")

    def write_duration_file(self, status):
        if self.duration_file is None:
            return
        lines = [f"attempt={self.attempt}", f"game_start_unix={self.game_start_unix:.6f}"]
        if self.first_move_unix is not None:
            lines.append(f"first_move_unix={self.first_move_unix:.6f}")
        if self.last_move_unix is not None:
            lines.append(f"last_move_unix={self.last_move_unix:.6f}")
        if status == "WIN":
            end_unix = time.time()
            lines.append(f"end_unix={end_unix:.6f}")
            lines.append(f"duration_seconds={end_unix - self.game_start_unix:.6f}")
        elif self.last_move_unix is not None:
            lines.append(f"duration_seconds={self.last_move_unix - self.game_start_unix:.6f}")
        else:
            lines.append(f"duration_seconds={status}")
        self.duration_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def set_cell(self, row, col, mark):
        if self.game_over:
            return "The game has already ended."
        # mark: 'F' fill, 'X' mark-empty, 'C' clear back to unknown
        if mark == "F":
            self.board[row][col] = 1
        elif mark == "X":
            self.board[row][col] = 2
        elif mark == "C":
            self.board[row][col] = 0
        else:
            return "Mark must be F (fill), X (mark empty), or C (clear)."
        self.mark_valid_move()
        if self.is_complete():
            self.game_over = True
            self.write_state_file()
            self.write_duration_file("WIN")
            return "Puzzle solved!"
        self.write_state_file()
        return "Move applied."

    def is_complete(self):
        # solved when every filled solution cell is filled, and no extra cell is filled
        for row in range(N):
            for col in range(N):
                want = self.solution[row][col]
                got = 1 if self.board[row][col] == 1 else 0
                if want != got:
                    return False
        return True

    def correct_filled(self):
        return sum(
            1
            for row in range(N)
            for col in range(N)
            if self.solution[row][col] == 1 and self.board[row][col] == 1
        )

    def wrong_filled(self):
        return sum(
            1
            for row in range(N)
            for col in range(N)
            if self.solution[row][col] == 0 and self.board[row][col] == 1
        )

    def board_lines(self):
        # column clues printed top-down above the grid
        col_strs = [[str(n) for n in clue] for clue in self.col_clues]
        max_col_h = max(len(c) for c in col_strs)
        row_clue_strs = [" ".join(str(n) for n in clue) for clue in self.row_clues]
        left_w = max(len(s) for s in row_clue_strs)

        lines = []
        for level in range(max_col_h):
            cells = []
            for c in range(N):
                idx = len(col_strs[c]) - max_col_h + level
                cells.append(col_strs[c][idx] if idx >= 0 else " ")
            lines.append(" " * (left_w + 3) + " ".join(cells))
        lines.append(" " * (left_w + 3) + "-" * (2 * N - 1))
        glyph = {0: ".", 1: "#", 2: "x"}
        for r in range(N):
            row_render = " ".join(glyph[self.board[r][c]] for c in range(N))
            lines.append(f"{row_clue_strs[r].rjust(left_w)} | {row_render}")
        return lines

    def write_state_file(self):
        status = "WIN" if self.game_over else "IN_PROGRESS"
        content = [f"Nonogram: {self.puzzle['label']} ({self.puzzle['name']})"]
        content.append("Legend: '#' filled, 'x' marked-empty, '.' unknown")
        content.append("Row clues are on the left; column clues are on top.")
        content.append("")
        content.extend(self.board_lines())
        content.append("")
        content.append(f"Filled cells correct: {self.correct_filled()} / {self.total_filled}")
        content.append(f"Filled cells that should be empty: {self.wrong_filled()}")
        content.append(f"Status: {status}")
        self.state_file.write_text("\n".join(content) + "\n", encoding="utf-8")

    def print_state(self):
        print(f"\nCurrent board is saved to: {self.state_file}")
        print(self.state_file.read_text(encoding="utf-8"), end="")

    def parse_command(self, raw):
        parts = raw.strip().split()
        if not parts:
            return None, "Please enter a command."
        if len(parts) != 3:
            return None, "Use 'row col F' (fill), 'row col X' (mark empty), or 'row col C' (clear)."
        try:
            row = int(parts[0])
            col = int(parts[1])
        except ValueError:
            return None, "Row and column must be integers."
        if not (0 <= row < N and 0 <= col < N):
            return None, f"Row and column must be between 0 and {N - 1}."
        mark = parts[2].upper()
        if mark not in ("F", "X", "C"):
            return None, "Third token must be F, X, or C."
        return ("set", row, col, mark), None

    def play(self):
        print(f"Nonogram started. Size: {self.puzzle['label']} ({self.puzzle['name']})")
        print("Enter 'row col F' to fill, 'row col X' to mark empty, 'row col C' to clear.")
        print(f"Rows and columns are zero-based: 0 to {N - 1}.")
        self.print_state()

        while not self.game_over:
            command = input("\nYour move: ")
            action, error = self.parse_command(command)
            if error:
                print(error)
                continue
            _, row, col, mark = action
            message = self.set_cell(row, col, mark)
            print(message)
            self.print_state()

        print("Congratulations!")


if __name__ == "__main__":
    state_file = sys.argv[1] if len(sys.argv) > 1 else None
    Nonogram(state_file).play()
