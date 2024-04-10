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

    move_up = f'{col}{row+1}'
    move_down = f'{col}{row-1}'
    move_left = f'{chr(ord(col)-1)}{row}'
    move_right = f'{chr(ord(col)+1)}{row}'

    move_up_right = f'{chr(ord(col)+1)}{row+1}'
    move_up_left = f'{chr(ord(col)-1)}{row+1}'
    move_down_right = f'{chr(ord(col)+1)}{row-1}'
    move_down_left = f'{chr(ord(col)-1)}{row-1}'

    possible_moves += [move for move in [move_up, move_down, move_left, move_right, move_up_right, move_up_left, move_down_right, move_down_left] if move in grid]

    return possible_moves