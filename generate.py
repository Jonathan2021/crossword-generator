import sys
from copy import deepcopy
import random
import time

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var, domain in self.domains.items():
            self.domains[var] =  [x for x in domain if len(x) == var.length]

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        xi, yi = self.crossword.overlaps[x, y] # Index of the overlap in x and y variables respectively
        y_letters = set(word[yi] for word in self.domains[y]) # The possible letters for y at the overlap

        length_before = len(self.domains[x])
        self.domains[x] = [word for word in self.domains[x] if word[xi] in y_letters] # Remove words in x's domain that have a letter at the overlap not present in any of y's domain
        return length_before != len(self.domains[x]) # True iif we removed some values in x's domain


    def _get_all_neighbors(self, variables= None):
        # Construct of a dictionary with elements of 'variables' as keys and the list of neighbors in present in 'variables' as values. If 'variables' is None, use all the variables from the puzzle
        neighbors = dict()
        if not variables:
            variables = self.crossword.variables

        # just a bit faster than calling neighbors on each but still O(n^2)
        for i, v1 in enumerate(variables):
            for v2 in list(variables)[i+1:]:
                if v2 != v1 and self.crossword.overlaps[v1, v2]:

                    # Add v2 as a neighbor of v1 and vice versa
                    if not v1 in neighbors:
                        neighbors[v1] = {v2}
                    else:
                        neighbors[v1].add(v2)
                    if not v2 in neighbors:
                        neighbors[v2] = {v1}
                    else:
                        neighbors[v2].add(v1)
        return neighbors

    def _get_arcs(self, variables = None):
        # Get the arcs of the binary constraint graph taking only 'variables' into account. If 'variables' is None then it's the set of all the puzzle's variables.
        neighbors = self._get_all_neighbors(variables)
        return [(v1, v2) for v1, v2s in neighbors.items() for v2 in v2s], neighbors

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """

        if not arcs:
            arcs, neighbors = self._get_arcs()
        else:
            neighbors = self._get_all_neighbors()

        while arcs:
            x, y = arcs.pop()
            if self.revise(x,y): # Prune x's domain
                if not self.domains[x]: # If x doesn't have any possible value left, then Failure
                    return False
                else:
                    # Add neighbors of x affected by the change (except y) to arcs
                    arcs = arcs + [(z,x) for z in neighbors[x] if z != y] # Neighbors will contain any of the variables from the puzzle. Not just the ones present in arcs. This is desirable as modification in domains in arcs can affect neighbors not present in arcs at first.
        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        # There shouldn't be some variables not in crossword are added to assignment
        return len(assignment.keys()) == len(self.crossword.variables)

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        
        vals = set()
        for var, val in assignment.items():
            if val in vals or len(val) != var.length: # Checking length is redondant in our implementation since we pruned all values that don't satisfy the unary constraint at the start. Still we keep it as it is part of consistency in the general backtracking algo to check unary constraints.
                return False
            vals.add(val)

        all_neighbors = self._get_all_neighbors(assignment.keys())

        for var, neighbors in all_neighbors.items():
            for n in neighbors:
                vari, ni = self.crossword.overlaps[var, n]
                if assignment[var][vari] != assignment[n][ni]:
                    return False
        return True
        
    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """

        neighbors = self.crossword.neighbors(var)
        unassigned_neighbors = neighbors - set(assignment.keys())

        constraint_list = list()
        index_letter_constraints = dict()

        # Dict with indices of var as keys and lists (not set as we may want duplicates) of letters in the neighbors of var at the overlapping position.
        for nbr in unassigned_neighbors:
            i, j = self.crossword.overlaps[var, nbr]
            if i not in index_letter_constraints:
                index_letter_constraints[i] = list()
            index_letter_constraints[i] += [nbr_val[j] for nbr_val in self.domains[nbr]]

        # For every value in var's domain, count the number of ruled out possible neighboring values.
        for var_val in self.domains[var]:
            constraint_list.append((
                    var_val,
                    sum([letter != var_val[index] for index, letters in index_letter_constraints.items() for letter in letters])
                    ))            

        # Shuffle to add some randomness in case of equal LCVs.
        random.shuffle(constraint_list)
        constraint_list.sort(key = lambda x: x[1])

        return [val for val, _ in constraint_list] # List ordered from least to most constraining

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        
        unassigned = list(self.crossword.variables - set(assignment.keys()))

        # Shuffle to add randomness in case both heuristics are equal
        random.shuffle(unassigned) 

        # Sort by increasing domain length and then decreasing degree
        unassigned.sort(key = lambda x: (len(self.domains[x]), -len(self.crossword.neighbors(x))))
        return unassigned[0] if unassigned else None

    def inference(self, var, assignment):
        # Making inferences given var assignment
        self.domains[var] = set([assignment[var]]) # Reduce var's domain to its assignment.
        arcs = [(n, var) for n in self.crossword.neighbors(var)] # add all arcs from neighbors to var

        # Apply ac3 with the arcs and propagate failure if there is no possible solution. If they may be a solution, add variables with domain length of 1 (1 possible value) as inferecences.
        return {x: self.domains[x][0] for x in set(self.domains.keys()) - set(assignment.keys()) if len(self.domains[x]) == 1} if self.ac3(arcs=arcs) else None


    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment # Yay we found a solution.
        var = self.select_unassigned_variable(assignment) # Select a variable acording to some heuristics
        
        for val in self.order_domain_values(var, assignment): # Order the selected variable's domain according to LCV 
            assignment[var] = val
            if self.consistent(assignment):
                old_domains = deepcopy(self.domains) # Keep track of the current domain state
                inferences = self.inference(var, assignment)

                # If inferences didn't result in a failure
                if inferences is not None: # Have to check is not None because if not then empty inference would mean failure if you did 'if inferences'
                    assignment.update(inferences) # Add the inferences to assignements
                
                    result = self.backtrack(assignment) # Backtrack deeper with the new assignments
                    if result:
                        return result # We propagate the solution back up
                    for inf in inferences: # Remove the made inferences from assignements
                        del assignment[inf]

                self.domains = old_domains # Restore the domain to its state
        del assignment[var]
        return None # This path results in a failure


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)


    start = time.time()
    assignment = creator.solve()
    end = time.time()
    print("Time: {}".format(end - start))
    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
