import sys
sys.path.append('/opt/homebrew/lib/python3.10/site-packages') # solve path problem
import itertools
import random
import math
from termcolor import colored

class Game_Control():
    def __init__(self, mines_number):
        self.real_mines = set()
        # initial the board with mines
        self.board = []
        for i in range(HEIGHT):
            row = []
            for j in range(WIDTH):
                row.append(False) # all cells are False initially
            self.board.append(row)
        while len(self.real_mines) != mines_number:
            i = random.randrange(HEIGHT)
            j = random.randrange(WIDTH)
            if not self.board[i][j]:
                self.real_mines.add((i, j))
                self.board[i][j] = True # randomly add mines
        print(colored("Secret! Mines are at:" + str(self.real_mines), "grey"))
        # initial safe cells
        self.inintial_safes = []
        inintial_steps = round(math.sqrt(HEIGHT * WIDTH))
        while len(self.inintial_safes) != inintial_steps:
            i = random.randrange(HEIGHT)
            j = random.randrange(WIDTH)
            if not self.board[i][j] and (i, j) not in self.inintial_safes:
                self.inintial_safes.append((i, j))
        print(colored("Initial safe cells:" + str(self.inintial_safes), "green"))

    def provide_hints(self, cell):
        #* provide the hints(number of surrounding mines)
        count = 0 # count of nearby mines
        # loop over all neighbor cells and record unmarked_cells
        for i in range(cell[0] - 1, cell[0] + 2):
            for j in range(cell[1] - 1, cell[1] + 2):
                if (i, j) == cell: # ignore itself
                    continue
                if (i, j) in self.real_mines: # update count
                    count += 1
        return count

    def print_board(self):
        #* print the resulting
        for i in range(HEIGHT):
            for j in range(WIDTH):
                if (i, j) in player.mines:
                    print(colored("X", "red"), end=' ')
                elif (i, j) in player.safes:
                    print(colored(self.provide_hints((i,j)), "green"), end=' ')
                else:
                    if (i, j) in self.real_mines:
                        print(colored("X", "grey"), end=' ')
                    else:
                        print(colored(self.provide_hints((i,j)), "grey"), end=' ')
            print("")

class AI_Player():
    def __init__(self):
        # safes / mines marked cells -> KB0
        self.mines = set()
        self.safes = set()
        # knowledge base
        self.KB = []
        # record remove list (produce when matching)
        self.matching_remove_list = []

    def mark_mine(self, cell):
        #* unit-propagation: handle a new positive single-literal clause
        #* mark the cell as mine and update KB
        self.mines.add(cell)
        self.KB = [clause for clause in self.KB if ("+",) + cell not in clause] # both positive -> remove
        for clause in self.KB:
            if ("-",) + cell in clause: # remove the cell from the multi-literal clause
                clause.remove(("-",) + cell)

    def mark_safe(self, cell):
        #* unit-propagation: handle a new negative single-literal clause
        #* mark the cell as safe and update KB
        self.safes.add(cell)
        self.KB = [clause for clause in self.KB if ("-",) + cell not in clause] # both negative -> remove
        for clause in self.KB:
            if ("+",) + cell in clause: # remove the cell from the multi-literal clause
                clause.remove(("+",) + cell)

    def unit_propagation(self, clause):
        #* check against all mine and safe cells
        for mine_cell in self.mines:
            if ("+",) + mine_cell in clause: # both positive -> don't add the clause to KB
                return None
            elif ("-",) + mine_cell in clause: # remove the cell from the multi-literal clause
                clause.remove(("-",) + mine_cell)
        for safe_cell in self.mines:
            if ("-",) + safe_cell in clause: # both negative -> don't add the clause to KB
                return None
            elif ("+",) + safe_cell in clause: # remove the cell from the multi-literal clause
                clause.remove(("+",) + safe_cell)
        return clause

    def subsumption(self, c1, c2):
        #* check whether c1 is subset of c2
        if c1.issubset(c2):
            return True
        else:
            return False

    def handle_hints(self, count, unmarked_cells):
        #* generate new clauses and insert them
        hint = (count, len(unmarked_cells)) # m, n
        new_clauses = self.generate_clauses(hint, unmarked_cells)
        for clause in new_clauses:
            self.insert_clause(clause)

    def generate_clauses(self, hint, cells):
        #* generate new clauses depending on the safe cell and hints
        new_clauses = []
        n, m = hint
        if n == m: # all cells are mines
            for i in range(0, m):
                new_clauses.append({("+", cells[i][0], cells[i][1])})
        elif n == 0: # all cells are safe
            for i in range(0, m):
                new_clauses.append({("-", cells[i][0], cells[i][1])})
        else: # general cases
            for positive_literals in itertools.combinations(cells, m-n+1): # C(m, m-n+1)
                clause = set()
                for cell in positive_literals:
                    clause.add(("+", cell[0], cell[1]))
                new_clauses.append(clause)
            for negative_literals in itertools.combinations(cells, n+1): # C(m, n+1)
                clause = set()
                for cell in negative_literals:
                    clause.add(("-", cell[0], cell[1]))
                new_clauses.append(clause)
        return new_clauses

    def insert_clause(self, clause):
        #* unit-propagate -> check duplication or subsumption
        # unit-propagate
        clause = self.unit_propagation(clause)
        if clause == None: # skip insertion because it is always true
            return
        # check duplication
        if clause in self.KB:
            return
        # check subsumption
        less_strict_list = []
        insert_flag = 1
        for old_clause in self.KB:
            if self.subsumption(clause, old_clause): # if new is subset of old
                less_strict_list.append(old_clause) # remove less strict one(old)
            if self.subsumption(old_clause, clause): # if old is subset of new 
                insert_flag = 0 # skip insertion
        for discard in less_strict_list: # remove all less strict elements
            try:
                self.KB.remove(discard)
            except:
                pass # duplication
        if insert_flag:
            self.KB.append(clause)

    def global_constraint(self, count):
        #* apply global constraint to solve the game
        unmarked_cells = []
        for i in range(HEIGHT):
            for j in range(WIDTH):
                if (i,j) not in self.safes and (i, j) not in self.mines: # unmarked
                    unmarked_cells.append((i, j))
        self.handle_hints(count, unmarked_cells)

    def matching(self, c1, c2):
        #* check duplication or subsumption -> complementary literals(resolution)
        # check duplication
        if c1 == c2:
            self.matching_remove_list.append(c1)
            return
        # check subsumption
        if self.subsumption(c1, c2): # check whether c1 is subset of c2
            self.matching_remove_list.append(c2) # remove less strict one(c2)
            return
        if self.subsumption(c2, c1): # check whether c2 is subset of c1
            self.matching_remove_list.append(c1) # remove less strict one(c1)
            return
        # complementary literals
        complementary_literals = []
        c1_set = {(x[1], x[2]) for x in c1}
        c2_set = {(x[1], x[2]) for x in c2}
        common_elements = c1_set.intersection(c2_set)
        for elements in common_elements:
            # the same cell and opposite symbol
            if ("+",) + elements in c1 and ("-",) + elements in c2:
                complementary_literals.append(elements)
            elif ("-",) + elements in c1 and ("+",) + elements in c2:
                complementary_literals.append(elements)
        if len(complementary_literals) == 1: # only one complementary literal -> resolution
            c1_set = {(x[1], x[2]) for x in c1}
            c2_set = {(x[1], x[2]) for x in c2}
            common_elements = c1_set.intersection(c2_set)
            complementary_literals = []
            for element in common_elements:
                if ("+",) + element in c1 and ("-",) + element in c2:
                    complementary_literals.append(element)
                elif ("-",) + element in c1 and ("+",) + element in c2:
                    complementary_literals.append(element)
            new_clause = c1 | c2 
            for element in complementary_literals:
                new_clause.discard(("+",) + element)
                new_clause.discard(("-",) + element)
            if len(new_clause) == 0:  # empty clause -> contradiction
                print(colored("Something wrong!!!!!", "red"))
                return
            self.insert_clause(new_clause)
        else: # more than one complementary literals -> insert c1 directly
            return

    def maintain_KB(self):
        #* follow the game flow to maintain KB
        no_marking = 0 # the number of rounds without new marked cells
        while True:
            # apply global constraint when unmarked cells is less than 9
            if HEIGHT * WIDTH - len(self.safes) + len(self.mines) <= 9:
                self.global_constraint(len(game.real_mines) - len(self.mines))
            exist_single = 0
            single_literal = []
            for clause in self.KB: # loop for all clauses to find single literal
                if len(clause) == 1:# single-literal clause
                    single_literal.append(clause)
            for single in single_literal: # remove single literal from KB
                try:
                    self.KB.remove(single)
                except:
                    pass # duplication
            # handle single literal
            while len(single_literal) > 0:
                exist_single = 1
                clause = single_literal.pop(0)
                cell = next(iter(clause))
                if cell[0] == "+": # mine
                    self.mark_mine(cell[1:])
                elif cell[0] == "-": # safe -> generate new clauses
                    self.mark_safe(cell[1:])
                    count = game.provide_hints(cell[1:])
                    # loop over all neighbor cells and record unmarked_cells
                    unmarked_cells = []
                    for i in range(cell[1] - 1, cell[1] + 2):
                        for j in range(cell[2] - 1, cell[2] + 2):
                            if (i, j) in self.safes: # ignore the safe cell
                                continue
                            elif (i, j) in self.mines: # ignore the mine cell and count--
                                count -= 1
                                continue
                            elif 0 <= i < HEIGHT and 0 <= j < WIDTH: # cell in the board
                                unmarked_cells.append((i, j))
                    self.handle_hints(count, unmarked_cells)
            if not exist_single: # pairwise matching
                no_marking += 1
                self.matching_remove_list = []
                for clause_pair in itertools.combinations(self.KB, 2):
                    c1, c2 = clause_pair
                    if len(c1) == 2 or len(c2) == 2:
                        self.matching(c1, c2)
                for discard in self.matching_remove_list:
                    try:
                        self.KB.remove(discard)
                    except:
                        pass # duplication
            else:
                no_marking = 0
            print(colored("KB : " + str(self.KB), "blue"))
            print(colored("All know safes: " + str(self.safes), "green"))
            print(colored("All know mines: " + str(self.mines), "red"))
            if len(self.safes) + len(self.mines) == HEIGHT * WIDTH: # marked all cells
                print(colored("Success!", "yellow"))
                game.print_board()
                break
            elif no_marking >= 10: # over ten rounds without marking new cells
                print(colored("Stuck!", "magenta"))
                game.print_board()
                break

if __name__ == "__main__":
    HEIGHT = 16
    WIDTH = 16
    MINES_NUMBER = 25
    # initial two main modules
    game = Game_Control(mines_number=MINES_NUMBER)
    player = AI_Player()
    # inital safe cells
    for init_move in game.inintial_safes:
        player.KB.append({("-", init_move[0], init_move[1])})
    # ai started to play the game
    player.maintain_KB()
