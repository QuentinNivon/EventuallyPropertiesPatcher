from enum import Enum

from utils import is_an_int, print_error, print_warning


class TransitionType(Enum):
    NEUTRAL = "BLACK"
    CORRECT = "GREEN"
    INCORRECT = "RED"


class Neighbourhood(Enum):
    GREEN = "G"
    RED = "R"
    GREEN_RED = "GR"
    GREEN_RED_BLACK = "GRB"
    NONE = ""


class State:
    def __init__(self, name, is_a_neighbourhood=False, neighbourhood_color=Neighbourhood.NONE):
        self.label = name
        self.inc_transitions = set()
        self.out_transitions = set()
        self.is_a_neighbourhood = is_a_neighbourhood
        self.color = neighbourhood_color
        self.processed = False

    def __str__(self):
        nb_inc_transitions = len(self.inc_transitions)
        nb_out_transitions = len(self.out_transitions)
        nb_transitions = nb_inc_transitions + nb_out_transitions

        neighbourhood_type = "a neighbourhood of type " + str(self.color) \
            if self.is_a_neighbourhood else "not a neighbourhood"

        inc_transitions_str = "- Incoming transitions:"
        out_transitions_str = "- Outgoing transitions:"

        for inc_trans in self.inc_transitions:
            inc_transitions_str += "\n     - " + str(inc_trans)

        for out_trans in self.out_transitions:
            out_transitions_str += "\n     - " + str(out_trans)

        return "State n°{} is {}. It has {} transitions. ({} incoming and {} outgoing).\n\n{}\n\n{}" \
            .format(self.label, neighbourhood_type, nb_transitions, nb_inc_transitions, nb_out_transitions,
                    inc_transitions_str, out_transitions_str)

    def __eq__(self, other):
        if isinstance(other, State):
            return self.label == other.label
        return False

    def __hash__(self):
        return hash(self.label)

    def mark_as_neighbourhood(self):
        self.is_a_neighbourhood = True

    def set_neighbourhood_color(self, color):
        self.color = color

    def add_inc_transition(self, transition):
        self.inc_transitions.add(transition)

    def add_out_transition(self, transition):
        self.out_transitions.add(transition)

    def set_processed(self):
        self.processed = True

    def stringify(self, visited_nodes, depth):
        nb_child = "no" if len(self.out_transitions) == 0 else str(len(self.out_transitions))

        string = "    " * depth
        string += "- State " + str(self.label) + " has " + nb_child + " child:\n"

        for transition in self.out_transitions:
            child = transition.out_state

            if child in visited_nodes:
                string += "    " * (depth + 1)
                string += "- State " + str(child.label) + " (end of loop)\n"
            else:
                visited_nodes.add(child)
                string += child.stringify(visited_nodes, depth + 1)

        return string


class Transition:
    def __init__(self, inc_state, out_state, label, transition_type):
        self.label = label
        self.transition_type = transition_type
        self.inc_state = inc_state
        self.out_state = out_state

    def __eq__(self, other):
        if isinstance(other, Transition):
            return self.inc_state == other.inc_state and self.out_state == other.out_state and self.label == other.label
        return False

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return "{} transition {} goes from state {} to state {}." \
            .format(self.transition_type, self.label, self.inc_state.label, self.out_state.label)

    def __hash__(self):
        return hash(self.inc_state) + hash(self.out_state)


class LtsParser:
    def __init__(self, red_transitions=None, green_transitions=None, black_transitions=None, initial_state=None,
                 nb_transitions=None, nb_states=None, states=None, transitions=None):
        if transitions is None:
            self.transitions = []
        else:
            self.transitions = transitions

        if states is None:
            self.states = []
        else:
            self.states = states

        if black_transitions is None:
            self.black_transitions = []
        else:
            self.black_transitions = black_transitions

        if green_transitions is None:
            self.green_transitions = []
        else:
            self.green_transitions = green_transitions

        if red_transitions is None:
            self.red_transitions = []
        else:
            self.red_transitions = red_transitions

        self.temp_states = {}
        self.initial_state = initial_state
        self.nb_transitions = nb_transitions
        self.nb_states = nb_states

    # Read the .autx file line by line to retrieve red, green and black transitions
    def parse(self, filename):
        with open(filename) as file:
            while line := file.readline().strip():
                if line.startswith("des"):
                    self.setup_general_infos(line)
                else:
                    self.add_transition(line)

        self.states = list(self.temp_states.values())
        del self.temp_states

    def setup_general_infos(self, line):
        opened_parenthesis = False
        nb_comas = 0
        initial_state = ""
        nb_transitions = ""
        nb_states = ""

        for char in line:
            if char == '(':
                opened_parenthesis = True
            elif char == ',':
                nb_comas += 1
            elif char == ')':
                opened_parenthesis = False
            else:
                if opened_parenthesis:
                    if nb_comas == 0:
                        initial_state += char
                    elif nb_comas == 1:
                        nb_transitions += char
                    else:
                        nb_states += char

        initial_state = initial_state.strip()
        nb_transitions = nb_transitions.strip()
        nb_states = nb_states.strip()

        if is_an_int(initial_state):
            self.initial_state = int(initial_state)

        if is_an_int(nb_transitions):
            self.nb_transitions = int(nb_transitions)

        if is_an_int(nb_states):
            self.nb_states = int(nb_states)

    def add_transition(self, line):
        first_coma = line.find(',')
        incoming_state = line[1: first_coma].strip()
        line2 = line[first_coma + 1:]
        second_coma = line2.rfind(',')
        transition = line2[0: second_coma].strip()
        outgoing_state = line2[second_coma + 1: len(line2) - 1]

        inc_state = parse_state(incoming_state)
        out_state = parse_state(outgoing_state)

        existing_inc_state = self.temp_states.get(inc_state.label)
        existing_out_state = self.temp_states.get(out_state.label)

        if existing_inc_state is not None:
            final_inc_state = existing_inc_state

            if inc_state.is_a_neighbourhood:
                final_inc_state.mark_as_neighbourhood()

            if inc_state.color is not None:
                final_inc_state.set_neighbourhood_color(inc_state.color)
        else:
            final_inc_state = inc_state
            self.temp_states[inc_state.label] = inc_state

        if existing_out_state is not None:
            final_out_state = existing_out_state

            if out_state.is_a_neighbourhood:
                final_out_state.mark_as_neighbourhood()

            if out_state.color is not None:
                final_out_state.set_neighbourhood_color(out_state.color)
        else:
            final_out_state = out_state
            self.temp_states[out_state.label] = out_state

        trans = parse_transition(transition, final_inc_state, final_out_state)
        final_out_state.add_inc_transition(trans)
        final_inc_state.add_out_transition(trans)

        if trans.transition_type == TransitionType.CORRECT:
            self.green_transitions.append(trans)
        elif trans.transition_type == TransitionType.INCORRECT:
            self.red_transitions.append(trans)
        else:
            self.black_transitions.append(trans)

        self.transitions.append(trans)


def parse_state(line):
    nb_dot = 0
    label = ""
    neighbourhood = ""
    neighbourhood_color = ""

    for char in line:
        if char == ':':
            nb_dot += 1
        else:
            if nb_dot == 0:
                label += char
            elif nb_dot == 1:
                neighbourhood += char
            else:
                neighbourhood_color += char

    label = label.strip()

    if is_an_int(label):
        label_int = int(label)
    else:
        print_error("Label must be an integer. Current is |{}|".format(label))
        raise Exception()

    is_a_neighbourhood = neighbourhood.strip() == "N"

    if neighbourhood_color.strip() == "G":
        neighbourhood_enum = Neighbourhood.GREEN
    elif neighbourhood_color.strip() == "R":
        neighbourhood_enum = Neighbourhood.RED
    elif neighbourhood_color.strip() == "GR":
        neighbourhood_enum = Neighbourhood.GREEN_RED
    elif neighbourhood_color.strip() == "GRB":
        neighbourhood_enum = Neighbourhood.GREEN_RED_BLACK
    else:
        if neighbourhood.strip() != "":
            print_warning("Neighbourhood type |{}| is unknown. Switched to no neighbourhood."
                          .format(neighbourhood_color.strip()))
        neighbourhood_enum = Neighbourhood.NONE

    return State(label_int, is_a_neighbourhood, neighbourhood_enum)


def parse_transition(line, inc_state, out_state):
    color_parsing = False
    label = ""
    color = ""

    for char in line:
        if char == ":":
            color_parsing = True
        else:
            if color_parsing:
                color += char
            else:
                if char != '"':
                    label += char

    label = label.strip()
    color = color.strip()

    if not color or color == "BLACK":
        transition_type = TransitionType.NEUTRAL
    elif color == "GREEN":
        transition_type = TransitionType.CORRECT
    elif color == "RED":
        transition_type = TransitionType.INCORRECT
    else:
        print_error("Transition type |{}| does not match any existing transition type.".format(color))
        raise Exception()

    # print(label)

    return Transition(inc_state, out_state, label, transition_type)
