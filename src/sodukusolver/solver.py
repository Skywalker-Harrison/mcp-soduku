"""
Sudoku solver implementation using bitmasks for efficient tracking of possible values.
"""

def isSafe(mat, i, j, num, row, col, box):
    """
    Check if it's safe to place 'num' at position (i, j) in the Sudoku grid.
    
    Args:
        mat: The Sudoku grid (9x9 matrix)
        i, j: The position to check
        num: The number to place (1-9)
        row, col, box: Bitmasks tracking occupied numbers in rows, columns, and 3x3 boxes
        
    Returns:
        bool: True if safe to place, False otherwise
    """
    if (row[i] & (1 << num)) or (col[j] & (1 << num)) or (box[i // 3 * 3 + j // 3] & (1 << num)):
        return False
    return True

def sudokuSolverRec(mat, i, j, row, col, box):
    """
    Recursive function to solve the Sudoku puzzle.
    
    Args:
        mat: The Sudoku grid (9x9 matrix)
        i, j: Current position in the grid
        row, col, box: Bitmasks tracking occupied numbers
        
    Returns:
        bool: True if the Sudoku can be solved, False otherwise
    """
    n = len(mat)

    # base case: Reached nth column of last row
    if i == n - 1 and j == n:
        return True

    # If reached last column of the row go to next row
    if j == n:
        i += 1
        j = 0

    # If cell is already occupied then move forward
    if mat[i][j] != 0:
        return sudokuSolverRec(mat, i, j + 1, row, col, box)

    for num in range(1, n + 1):
        # If it is safe to place num at current position
        if isSafe(mat, i, j, num, row, col, box):
            mat[i][j] = num

            # Update masks for the corresponding row, column and box
            row[i] |= (1 << num)
            col[j] |= (1 << num)
            box[i // 3 * 3 + j // 3] |= (1 << num)

            if sudokuSolverRec(mat, i, j + 1, row, col, box):
                return True

            # Unmask the number num in the corresponding row, column and box masks
            mat[i][j] = 0
            row[i] &= ~(1 << num)
            col[j] &= ~(1 << num)
            box[i // 3 * 3 + j // 3] &= ~(1 << num)

    return False

def solveSudoku(mat):
    """
    Solve a Sudoku puzzle.
    
    Args:
        mat: The Sudoku grid (9x9 matrix) with 0s for empty cells
        
    Returns:
        bool: True if solved successfully, False otherwise
    """
    n = len(mat)
    row = [0] * n
    col = [0] * n
    box = [0] * n

    # Set the bits in bitmasks for values that are initially present
    for i in range(n):
        for j in range(n):
            if mat[i][j] != 0:
                row[i] |= (1 << mat[i][j])
                col[j] |= (1 << mat[i][j])
                box[(i // 3) * 3 + j // 3] |= (1 << mat[i][j])

    return sudokuSolverRec(mat, 0, 0, row, col, box)

def parse_sudoku_text(text):
    """
    Parse a Sudoku puzzle from text input.
    
    The input can be in various formats:
    - Space or comma-separated values (0 or . for empty cells)
    - Multiple lines representing rows
    
    Args:
        text: String containing the Sudoku puzzle
        
    Returns:
        list: 9x9 matrix representing the Sudoku puzzle
    """
    # Initialize an empty 9x9 grid
    grid = []
    
    # Split the input into lines
    lines = [line.strip() for line in text.strip().split('\n') if line.strip()]
    
    # If we have a single line, try to parse it as a flat representation
    if len(lines) == 1:
        # Replace common separators with spaces
        flat = lines[0].replace(',', ' ').replace(';', ' ')
        # Replace dots with zeros
        flat = flat.replace('.', '0')
        # Split by whitespace and filter out empty strings
        values = [v for v in flat.split() if v]
        
        # Check if we have enough values
        if len(values) != 81:
            raise ValueError(f"Expected 81 values for a 9x9 Sudoku, got {len(values)}")
        
        # Create the 9x9 grid
        for i in range(9):
            row = []
            for j in range(9):
                cell = values[i * 9 + j]
                try:
                    row.append(int(cell))
                except ValueError:
                    raise ValueError(f"Invalid Sudoku value: {cell}")
            grid.append(row)
    else:
        # Parse multiple lines
        for line in lines:
            if not line.strip():
                continue
                
            # Replace dots with zeros and remove other common separators
            line = line.replace('.', '0').replace(',', ' ').replace(';', ' ')
            # Split and filter
            values = [v for v in line.split() if v]
            
            row = []
            for cell in values:
                try:
                    row.append(int(cell))
                except ValueError:
                    raise ValueError(f"Invalid Sudoku value: {cell}")
            
            if row:
                grid.append(row)
    
    # Validate the grid dimensions
    if len(grid) != 9:
        raise ValueError(f"Expected 9 rows for Sudoku, got {len(grid)}")
    
    for i, row in enumerate(grid):
        if len(row) != 9:
            raise ValueError(f"Expected 9 columns in row {i}, got {len(row)}")
    
    # Validate the values (0-9 only)
    for i in range(9):
        for j in range(9):
            if not 0 <= grid[i][j] <= 9:
                raise ValueError(f"Invalid value {grid[i][j]} at position ({i}, {j})")
    
    return grid

def format_sudoku_grid(grid):
    """
    Format a Sudoku grid for display.
    
    Args:
        grid: 9x9 Sudoku grid
        
    Returns:
        str: Formatted string representation of the grid
    """
    result = []
    
    horizontal_line = "+-------+-------+-------+"
    
    for i in range(9):
        if i % 3 == 0:
            result.append(horizontal_line)
        
        row = "| "
        for j in range(9):
            row += str(grid[i][j]) + " "
            if (j + 1) % 3 == 0:
                row += "| "
                
        result.append(row)
        
    result.append(horizontal_line)
    
    return "\n".join(result) 