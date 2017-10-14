"""
regex.py
A regular expression parser and matcher.
Author: Andrew Chan
Email: andrewkchan@berkeley.edu
License: MIT
"""

class RegexGraphState:
    _state_id = 0
    _SPLIT = "SPLIT"
    _MATCH = "MATCH"
    c = "a" # the character matching the output of this state, or else == _SPLIT if this is a splitting state
            # or _MATCH if this is a matching state
    #out = [] # list of RegexGraphState objects that this state points to
    def __init__(self, c, out = None):
        self.c = c
        if out is None:
            out = []
        self.out = out
        self._state_id = RegexGraphState._state_id
        RegexGraphState._state_id += 1
    def __eq__(self, other):
        return isinstance(other, RegexGraphState) and self._state_id == other._state_id
    def __neq__(self, other):
        return not self == other
    def __hash__(self):
        return self._state_id


class RegexGraphFragment:
    start = None # the starting state of the graph
    out_states = [] # list of RegexGraphState objects that are possible end states of this graph
                    # we do NOT end in a matching state. this list is basically used for setting all out
                    # pointers of the end states to a given end state, since RegexGraphFragments
                    # are like components of the graph that have a single input and lead to a single output
                    # (but can be really complicated in the middle)
    def __init__(self, start, out_states):
        self.start = start
        self.out_states = out_states
    def set_out(self, next_frag):
        """
        Set the out arrows of our endpoints to point to the start of the fragment next_frag.
        """
        if not isinstance(next_frag, RegexGraphFragment):
            raise Exception("set_out param should be fragment")
        for state in self.out_states:
            state.out.clear()
            state.out.append(next_frag.start)


def infix_to_postfix(regex_str):
    """
    Converts a regular expression in infix notation to postfix notation.
    Also adds concatenation operators ("."), which are implicit in normal regular expressions.
    For example, the expression /a(bb)+|cde/ becomes /abb.+.cde..|/, where "." concatenates 2 operands.
    """
    output = [] # output stack
    operators = [] #operators stack
    op_precedence = {"|": 0, ".": 1, "?": 2, "+": 2, "*": 2} # higher value == higher precedence

    def add_operator(op):
        if len(operators) == 0:
            operators.append(op)
            return
        while len(operators) > 0:
            last_operator = operators[-1]
            if op_precedence[op] < op_precedence[last_operator]:
                output.append(operators.pop())
            else:
                break
        operators.append(op)
        return

    i = 0
    while i < len(regex_str):
        #print("left to parse:" + regex_str[i:])
        char = regex_str[i]
        if char in op_precedence:
            # current character is an operator
            add_operator(char)
        elif char == "(":
            if i > 0 and regex_str[i-1] not in op_precedence:
                # if previous char was letter, then add implicit concatenation operator
                add_operator(".")
            sub_expr = infix_to_postfix(regex_str[i+1:])
            i += len(sub_expr)
            output = output + sub_expr
        elif char == ")":
            break
        else:
            if i > 0 and regex_str[i-1] not in op_precedence:
                add_operator(".")
            output.append(char)
        i += 1
    # reached end of string, push all operators onto output stack
    while len(operators) > 0:
        output.append(operators.pop())
    return output


def parse_regex(regex_str):
    """
    Builds a regular expression graph from the input regular expression string.
    :param: regex_str - The input regular expression string
    :output: A regular expression state at the root of a regex state graph.
    """
    postfix_str = "".join(infix_to_postfix(regex_str))
    i = 0
    operators = set([".", "|", "*", "?", "+"])
    leaf_stack = []
    while i < len(postfix_str):
        char = postfix_str[i]
        if char in operators:
            if char == ".":
                # concatenation operator, concatenate last 2 operands into state (oldest goes on left)
                f2 = leaf_stack.pop()
                f1 = leaf_stack.pop()
                f1.set_out(f2)
                concatenated = RegexGraphFragment(f1.start, out_states=f2.out_states)
                leaf_stack.append(concatenated)
            elif char == "+":
                # "1 or more" operator. Start at fragment and either go to end or loop back to beginning
                f = leaf_stack.pop()
                split = RegexGraphState(c=RegexGraphState._SPLIT, out=[f.start])
                add_frag = RegexGraphFragment(f.start, out_states=[split])
                leaf_stack.append(add_frag)
            elif char == "?":
                # "0 or 1" operator. Start with split, either go to end or into fragment
                f = leaf_stack.pop()
                split = RegexGraphState(c=RegexGraphState._SPLIT, out=[f.start])
                check_frag = RegexGraphFragment(split, out_states=[split] + f.out_states)
                leaf_stack.append(check_frag)
            elif char == "*":
                # "0 or more" operator. Start with split, either go to end or into fragment.
                # fragment then goes back into split.
                f = leaf_stack.pop()
                split = RegexGraphState(c=RegexGraphState._SPLIT, out=[f.start])
                any_frag = RegexGraphFragment(split, out_states=[split])
                f.set_out(any_frag)
                leaf_stack.append(any_frag)
            elif char == "|":
                # OR operator (alternation). Start with split, go into either of last 2 operands
                f2 = leaf_stack.pop()
                f1 = leaf_stack.pop()
                split = RegexGraphState(c=RegexGraphState._SPLIT, out=[f1.start, f2.start])
                or_frag = RegexGraphFragment(split, out_states=f1.out_states + f2.out_states)
                leaf_stack.append(or_frag)
        else:
            # not an operator, just use the default (character) graph state
            s = RegexGraphState(c=char)
            leaf_stack.append(RegexGraphFragment(s, [s]))
        i += 1
    # finished parsing all of regex_str
    # should only be 1 fragment left in stack. if more, error. else, set out states to a matching state
    if len(leaf_stack) != 1:
        raise Exception()
    matching_state = RegexGraphState(c=RegexGraphState._MATCH)
    matching_state_frag = RegexGraphFragment(matching_state, out_states=[])
    graph_frag = leaf_stack.pop()
    #print(graph_frag.out_states)
    graph_frag.set_out(matching_state_frag)
    return graph_frag.start

def add_state(state, next_states):
    """
    Adds the input state to the set of next states, expanding a split if necessary.
    """
    if state.c == state._SPLIT:
        out_states = state.out
        for out in out_states:
            add_state(out, next_states)
    else:
        next_states.add(state)

def step(states, char):
    """
    Given a set of input states and a character, returns a set of the states in the next step.
    """
    next_states = set()
    for s in states:
        if s.c == char:
            for next_s in s.out:
                add_state(next_s, next_states)
    return next_states

def match_str(input_str, regex_str):
    regex_graph = parse_regex(regex_str)
    current_states = set()
    add_state(regex_graph, current_states)

    i = 0
    while i < len(input_str):
        current_states = step(current_states, input_str[i])
        i += 1

    for s in current_states:
        if s.c == RegexGraphState._MATCH:
            return True
    return False

if __name__ == "__main__":
    print(infix_to_postfix("Ext"))
    print(match_str("Ext", "Ext"))