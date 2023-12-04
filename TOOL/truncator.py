from enum import Enum

from lts_parser import TransitionType, State, Transition
from utils import parse_property, transition_updates_property, print_error


class Truncation(Enum):
    FULL_AFTER_LIVENESS = 0
    FULL = 1
    RED = 2
    GREEN_AFTER_LIVENESS = 3
    GREEN = 4
    NO_TRUNCATION = 5


class Truncator:
    def __init__(self, clts_parser, override, mcl_file):
        self.clts_parser = clts_parser
        self.override = override
        self.property = parse_property(mcl_file)

    def truncate(self, truncation):
        initial_state = get_initial_state(self.clts_parser.states)

        if truncation == Truncation.FULL:
            self.truncate_all_green_rec(initial_state, set(), False)
            self.truncate_all_red_rec(initial_state, set(), False)
            self.add_red_sink_state()
            self.add_green_sink_state()
        elif truncation == Truncation.FULL_AFTER_LIVENESS:
            self.truncate_green_after_liveness_rec(initial_state, set(), False, 0)
            self.truncate_all_red_rec(initial_state, set(), False)
            self.add_red_sink_state()
            self.add_green_sink_state()
        elif truncation == Truncation.RED:
            self.truncate_all_red_rec(initial_state, set(), False)
            self.add_red_sink_state()
        elif truncation == Truncation.GREEN:
            self.truncate_all_green_rec(initial_state, set(), False)
            self.add_green_sink_state()
        elif truncation == Truncation.GREEN_AFTER_LIVENESS:
            self.truncate_green_after_liveness_rec(initial_state, set(), False, 0)
            self.add_green_sink_state()
        elif truncation == Truncation.NO_TRUNCATION:
            pass
        else:
            print_error("Truncation type |{}| is not supported.".format(truncation.value))
            raise Exception()

        self.clts_parser.nb_transitions = len(self.clts_parser.transitions)
        self.clts_parser.nb_states = len(self.clts_parser.states)

    def truncate_all_green_rec(self, current_state, visited_states, should_be_removed):
        if current_state in visited_states:
            return

        visited_states.add(current_state)

        for transition in current_state.out_transitions:
            if transition.transition_type == TransitionType.CORRECT:
                if should_be_removed:
                    try:
                        self.clts_parser.transitions.remove(transition)
                        self.clts_parser.green_transitions.remove(transition)
                    except ValueError:
                        print_error("Transitions should never be duplicated!")
                        raise Exception()

                    try:
                        self.clts_parser.states.remove(transition.out_state)
                    except ValueError:
                        # Do nothing because the current state may have already been removed
                        pass

                self.truncate_all_green_rec(transition.out_state, visited_states, True)
            else:
                self.truncate_all_green_rec(transition.out_state, visited_states, False)

    def truncate_green_after_liveness_rec(self, current_state, visited_states, should_be_removed, advancement):
        if current_state in visited_states:
            return

        visited_states.add(current_state)

        for transition in current_state.out_transitions:
            current_advancement = advancement + 1 if transition_updates_property(self.property, transition,
                                                                                 advancement) else advancement

            if transition.transition_type == TransitionType.CORRECT:
                if should_be_removed:
                    try:
                        self.clts_parser.transitions.remove(transition)
                        self.clts_parser.green_transitions.remove(transition)
                    except ValueError:
                        print_error("Transitions should never be duplicated!")
                        raise Exception()

                    try:
                        self.clts_parser.states.remove(transition.out_state)
                    except ValueError:
                        # Do nothing because the current state may have already been removed
                        pass

                property_validated = current_advancement == len(self.property)
                current_start_removing = should_be_removed or property_validated

                self.truncate_green_after_liveness_rec(
                    transition.out_state,
                    visited_states,
                    current_start_removing,
                    current_advancement
                )

            else:
                self.truncate_green_after_liveness_rec(transition.out_state, visited_states, False, advancement)

    def truncate_all_red_rec(self, current_state, visited_states, should_be_removed):
        if current_state in visited_states:
            return

        visited_states.add(current_state)

        for transition in current_state.out_transitions:
            if transition.transition_type == TransitionType.INCORRECT:
                if should_be_removed:
                    try:
                        self.clts_parser.transitions.remove(transition)
                        self.clts_parser.red_transitions.remove(transition)
                    except ValueError:
                        print_error("Transitions should never be duplicated!")
                        raise Exception()

                    try:
                        self.clts_parser.states.remove(transition.out_state)
                    except ValueError:
                        # Do nothing because the current state may have already been removed
                        pass

                self.truncate_all_red_rec(transition.out_state, visited_states, True)

            else:
                self.truncate_all_red_rec(transition.out_state, visited_states, False)

    def add_red_sink_state(self):
        to_red_sink_transitions = set()
        self.get_to_red_sink_transitions(get_initial_state(self.clts_parser.states), to_red_sink_transitions, set())
        sink_state = State(-2)
        self.clts_parser.states.append(sink_state)

        for transition in to_red_sink_transitions:
            self.clts_parser.transitions.remove(transition)
            self.clts_parser.red_transitions.remove(transition)

            try:
                self.clts_parser.states.remove(transition.out_state)
            except ValueError:
                pass

            new_transition = Transition(transition.inc_state, sink_state, transition.label, TransitionType.INCORRECT)
            self.clts_parser.transitions.append(new_transition)
            self.clts_parser.red_transitions.append(new_transition)

    def add_green_sink_state(self):
        to_green_sink_transitions = set()
        self.get_to_green_sink_transitions(get_initial_state(self.clts_parser.states), to_green_sink_transitions, set())
        sink_state = State(-1)
        self.clts_parser.states.append(sink_state)

        for transition in to_green_sink_transitions:
            self.clts_parser.transitions.remove(transition)
            self.clts_parser.green_transitions.remove(transition)

            try:
                self.clts_parser.states.remove(transition.out_state)
            except ValueError:
                pass

            new_transition = Transition(transition.inc_state, sink_state, transition.label, TransitionType.CORRECT)
            self.clts_parser.transitions.append(new_transition)
            self.clts_parser.green_transitions.append(new_transition)

    def get_to_red_sink_transitions(self, current_state, to_red_sink_transitions, visited_states):
        if current_state in visited_states:
            return

        visited_states.add(current_state)

        for transition in current_state.out_transitions:
            if transition.transition_type == TransitionType.INCORRECT:
                # A red transition necessarily goes to sink state as red part has been fully truncated
                to_red_sink_transitions.add(transition)
            elif transition.transition_type == TransitionType.NEUTRAL:
                self.get_to_red_sink_transitions(transition.out_state, to_red_sink_transitions, visited_states)

    def get_to_green_sink_transitions(self, current_state, to_green_sink_transitions, visited_states):
        if current_state in visited_states:
            return

        visited_states.add(current_state)

        for transition in current_state.out_transitions:
            if transition.transition_type == TransitionType.CORRECT:
                if (transition.out_state.out_transitions == set()
                        or next(iter(transition.out_state.out_transitions)) not in self.clts_parser.green_transitions):
                    to_green_sink_transitions.add(transition)
                else:
                    self.get_to_green_sink_transitions(transition.out_state, to_green_sink_transitions, visited_states)
            elif transition.transition_type == TransitionType.NEUTRAL:
                self.get_to_green_sink_transitions(transition.out_state, to_green_sink_transitions, visited_states)


def get_initial_state(states):
    for state in states:
        if state.inc_transitions == set():
            return state

    print_error("No initial state could be found.")
    raise Exception()
