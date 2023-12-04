import utils
from lts_parser import State, TransitionType, Transition, LtsParser, Neighbourhood
from utils import parse_property, transition_updates_property, print_error, print_verbose


class CounterexamplesGenerator:
    def __init__(self, lts_parser, mcl_file):
        self.red_transitions = []
        self.green_transitions = []
        self.black_transitions = []
        self.states = []
        self.transitions = []
        self.lts_parser = lts_parser
        # Correspondence between a tuple (state_label, transition_label, transition_type) and a state
        self.states_trans_correspondence = dict()
        self.current_state_label = 0
        self.property = parse_property(mcl_file)

        if utils.VERBOSE:
            print_verbose("Property is: {}".format(self.property))

    def generate(self):
        old_initial_state = get_initial_state(self.lts_parser.states)
        new_initial_state = State(self.current_state_label)
        self.states.append(new_initial_state)
        self.update_state_label()
        # First, we generate the CLTS and color in green all the transitions that are satisfying the property
        # or successors of transitions that are satisfying the property
        self.generate_rec(old_initial_state, new_initial_state, False, 0)
        print("1) CLTS generated")
        # Then, we color in red all the black transitions that can never reach a green transition
        self.add_red_transitions(new_initial_state, {}, {})
        print("2) Red transitions added")
        # Finally, we color in green all the black transitions that can only reach green transitions
        self.finalize_green_part(new_initial_state, {}, {})
        print("3) Green part finalized")
        # One last traversal to compute neighbourhoods
        compute_neighbourhoods(new_initial_state, {})
        print("4) Neighbourhoods computed")
        # Characterization of the transitions
        self.characterize_transitions()
        print("5) Transitions characterized")

        return LtsParser(self.red_transitions, self.green_transitions, self.black_transitions, new_initial_state.label,
                         len(self.transitions), len(self.states), self.states, self.transitions)

    def generate_rec(self, old_state, new_state, property_validated, advancement):
        for transition in old_state.out_transitions:
            old_out_state = transition.out_state
            current_advancement = advancement + 1 \
                if transition_updates_property(self.property, transition, advancement) \
                else advancement
            property_locally_validated = property_validated or (current_advancement == len(self.property))
            pursue_recursion = True

            if property_locally_validated:
                transition_type = TransitionType.CORRECT
            else:
                transition_type = TransitionType.NEUTRAL

            key = (old_state, transition.label, transition_type, current_advancement)
            existing_out_state = self.states_trans_correspondence.get(key)

            if existing_out_state is not None:
                new_out_state = existing_out_state
                pursue_recursion = False
            else:
                new_out_state = State(self.current_state_label)
                self.update_state_label()
                self.states_trans_correspondence[key] = new_out_state
                self.states.append(new_out_state)

            new_transition = Transition(new_state, new_out_state, transition.label, transition_type)
            new_state.add_out_transition(new_transition)
            new_out_state.add_inc_transition(new_transition)
            self.transitions.append(new_transition)

            if pursue_recursion:
                self.generate_rec(old_out_state, new_out_state, property_locally_validated, current_advancement)

    def add_red_transitions(self, state, visited_states, computed_transitions):
        if state.label in visited_states:
            return

        visited_states[state.label] = True

        for transition in state.out_transitions:
            if transition.transition_type == TransitionType.NEUTRAL:
                key = (transition.inc_state.label, transition.label, transition.out_state.label)
                value = computed_transitions.get(key)

                if value is None:
                    current_transition_can_reach_green = self.transition_can_reach_green(transition, {},
                                                                                         computed_transitions)
                    computed_transitions[key] = current_transition_can_reach_green
                else:
                    current_transition_can_reach_green = value

                if current_transition_can_reach_green:
                    self.add_red_transitions(transition.out_state, visited_states, computed_transitions)
                else:
                    self.color_transition_and_successors_in_red(transition)

    def finalize_green_part(self, state, visited_states, computed_transitions):
        if state.label in visited_states:
            return

        visited_states[state.label] = True

        for transition in state.out_transitions:
            if transition.transition_type == TransitionType.NEUTRAL:
                key = (transition.inc_state.label, transition.label, transition.out_state.label)
                value = computed_transitions.get(key)

                if value is None:
                    current_transition_can_reach_green_or_black_only = self.transition_can_reach_green_or_black_only(
                        transition, {}, computed_transitions)
                    computed_transitions[key] = current_transition_can_reach_green_or_black_only
                else:
                    current_transition_can_reach_green_or_black_only = value

                if current_transition_can_reach_green_or_black_only:
                    transition.transition_type = TransitionType.CORRECT

            self.finalize_green_part(transition.out_state, visited_states, computed_transitions)

    def characterize_transitions(self):
        for transition in self.transitions:
            if transition.transition_type == TransitionType.CORRECT:
                self.green_transitions.append(transition)
            elif transition.transition_type == TransitionType.NEUTRAL:
                self.black_transitions.append(transition)
            else:
                self.red_transitions.append(transition)

    def update_state_label(self):
        self.current_state_label += 1

    def transition_can_reach_green(self, transition, visited_transitions, computed_transitions):
        key = (transition.inc_state.label, transition.label, transition.out_state.label)

        if key in visited_transitions:
            return transition == TransitionType.CORRECT

        visited_transitions[key] = True

        value = computed_transitions.get(key)

        if value is not None:
            return value

        if transition.transition_type == TransitionType.CORRECT:
            computed_transitions[key] = True
            return True

        for out_transition in transition.out_state.out_transitions:
            next_key = (out_transition.inc_state.label, out_transition.label, out_transition.out_state.label)
            next_value = computed_transitions.get(next_key)

            if next_value is not None and next_value:
                return True

            if out_transition.transition_type == TransitionType.CORRECT:
                computed_transitions[next_key] = True
                return True

            next_transition_can_reach_green = self.transition_can_reach_green(out_transition, visited_transitions,
                                                                              computed_transitions)
            computed_transitions[next_key] = next_transition_can_reach_green

            if next_transition_can_reach_green:
                return True

        computed_transitions[key] = False
        return False

    def transition_can_reach_green_or_black_only(self, transition, visited_transitions, computed_transitions):
        key = (transition.inc_state.label, transition.label, transition.out_state.label)

        if key in visited_transitions:
            return transition.transition_type != TransitionType.INCORRECT

        visited_transitions[key] = True

        value = computed_transitions.get(key)

        if value is not None:
            return value

        if transition.transition_type == TransitionType.INCORRECT:
            computed_transitions[key] = False
            return False

        for out_transition in transition.out_state.out_transitions:
            next_key = (out_transition.inc_state.label, out_transition.label, out_transition.out_state.label)
            next_value = computed_transitions.get(next_key)

            if next_value is not None and not next_value:
                return False

            if out_transition.transition_type == TransitionType.INCORRECT:
                computed_transitions[next_key] = False
                return False

            next_transition_can_reach_only_black_or_green = self.transition_can_reach_green_or_black_only(
                out_transition, visited_transitions, computed_transitions)

            computed_transitions[next_key] = next_transition_can_reach_only_black_or_green

            if not next_transition_can_reach_only_black_or_green:
                return False

        computed_transitions[key] = True
        return True

    def color_transition_and_successors_in_red(self, transition):
        self.color_transition_and_successors_in_red_rec(transition, {})

    def color_transition_and_successors_in_red_rec(self, transition, visited_transition):
        key = (transition.inc_state.label, transition.label, transition.out_state.label)

        if key in visited_transition:
            return

        visited_transition[key] = True
        transition.transition_type = TransitionType.INCORRECT

        for out_transition in transition.out_state.out_transitions:
            self.color_transition_and_successors_in_red_rec(out_transition, visited_transition)


def get_initial_state(states):
    for state in states:
        if state.inc_transitions == set():
            return state

    print_error("No initial state found in the states list.")
    raise Exception()


def state_is_a_neighbourhood(state):
    return state_has_at_least_one_neutral_incoming_transition(state) \
           and state_has_at_least_one_non_neutral_outgoing_transition(state)


def state_has_at_least_one_neutral_incoming_transition(state):
    if state.inc_transitions == set():
        return True  # Initial state case

    for inc_transition in state.inc_transitions:
        if inc_transition.transition_type == TransitionType.NEUTRAL:
            return True

    return False


def state_has_at_least_one_non_neutral_outgoing_transition(state):
    for out_transition in state.out_transitions:
        if out_transition.transition_type != TransitionType.NEUTRAL:
            return True

    return False


def compute_neighbourhood_type(state):
    # In this method, we assume that the given state is a neighbourhood
    has_red_out = False
    has_green_out = False
    has_black_out = False

    for out_transition in state.out_transitions:
        if out_transition.transition_type == TransitionType.NEUTRAL:
            has_black_out = True
        if out_transition.transition_type == TransitionType.CORRECT:
            has_green_out = True
        if out_transition.transition_type == TransitionType.INCORRECT:
            has_red_out = True

    if has_green_out:
        if has_red_out:
            if has_black_out:
                return Neighbourhood.GREEN_RED_BLACK
            else:
                return Neighbourhood.GREEN_RED
        else:
            return Neighbourhood.GREEN
    elif has_red_out:
        return Neighbourhood.RED
    else:
        print_error("State {} was expected to be a neighbourhood but is actually not!".format(state))
        raise Exception()


def compute_neighbourhoods(state, visited_states):
    if state.label in visited_states:
        return

    visited_states[state.label] = True

    if state_is_a_neighbourhood(state):
        state.mark_as_neighbourhood()
        state.set_neighbourhood_color(compute_neighbourhood_type(state))

    for out_transition in state.out_transitions:
        compute_neighbourhoods(out_transition.out_state, visited_states)
