# This class is used to verify that the generated CLTS is semantically correct,
# meaning that there is no transition belonging to it that is either:
# - Red and can reach black or green transitions
# - Green and can reach black or red transitions
# If this is the case, then the CLTS is badly formed.
import utils
from lts_parser import TransitionType


class Verifier:
    def __init__(self, initial_state):
        self.initial_state = initial_state

    def verify(self):
        visited_transitions = set()

        for transition in self.initial_state.out_transitions:
            if not self.verify_rec(transition, visited_transitions, transition.transition_type):
                return False

        return True

    def verify_rec(self, transition, visited_transitions, expected_type):
        if transition in visited_transitions:
            transition_is_valid = True if expected_type == TransitionType.NEUTRAL\
                                        else transition.transition_type == expected_type

            if not transition_is_valid and utils.VERBOSE:
                utils.print_verbose("{} should be of type {}. Current is {}."
                      .format(transition, expected_type.value, transition.transition_type.value))

            return transition_is_valid

        visited_transitions.add(transition)

        if expected_type != TransitionType.NEUTRAL:
            new_transition_type = expected_type
            if transition.transition_type != expected_type:
                if utils.VERBOSE:
                    utils.print_verbose("{} should be of type {}. Current is {}."
                          .format(transition, expected_type.value, transition.transition_type.value))
                return False
        else:
            new_transition_type = transition.transition_type

        for out_transition in transition.out_state.out_transitions:
            if not self.verify_rec(out_transition, visited_transitions, new_transition_type):
                if utils.VERBOSE:
                    utils.print_verbose("{} should be of type {}. Current is {}."
                          .format(transition, expected_type.value, transition.transition_type.value))
                return False

        return True
