def create_grid():
    columns = list("ABCDEFGHIJ")
    rows = list(range(1, 11))
    grid = []
    for c in columns:
        for r in rows:
            grid.append(f'{c}{r}')
    return grid


def getColumnCharacterToNumber(character):
    return ord(character.upper()) - 64


def get_movable_coordinates(position, grid):
    col, row = position[0], position[1:]
    row = int(row)
    possible_moves = []

    # Generate moves within 2 squares in any direction
    directions = [-2, -1, 0, 1, 2]
    for d_col in directions:
        for d_row in directions:
            # Skip the current position (0,0 offset)
            if d_col == 0 and d_row == 0:
                continue
            new_col = chr(ord(col) + d_col)
            new_row = row + d_row
            new_position = f'{new_col}{new_row}'
            if new_position in grid:
                possible_moves.append(new_position)

    return possible_moves