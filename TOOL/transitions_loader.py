import utils
from lts_parser import TransitionType
from utils import transition_in_set


# Class used to compute the transitions belonging to the sets ART, FRT and URT
# As transitions are uniquely defined by the tuple (inc_state, out_state, label),
# and as we want only uniquely labelled transitions here, we verify that a transition
# of same label is not already in the set before adding it to the set.


class TransitionsLoader:
    def __init__(self, all_transitions):
        self.art = set()
        self.frt = set()
        self.urt = set()
        self.all_transitions = all_transitions

        if utils.VERBOSE:
            utils.print_verbose("Transitions set has {} transitions.".format(len(all_transitions)))

    def load_subsets(self):
        self.load_art()
        self.load_frt()
        self.load_urt()
        self.correct_art()
        print("ART has {} transitions.".format(len(self.art)))
        print("FRT has {} transitions.".format(len(self.frt)))
        print("URT has {} transitions.".format(len(self.urt)))

    def load_art(self):
        for transition in self.all_transitions:
            if transition.transition_type == TransitionType.INCORRECT and transition not in self.art:
                self.art.add(transition)

        if utils.VERBOSE:
            utils.print_verbose("ART has {} transitions:".format(len(self.art)))

            for transition in self.art:
                utils.print_verbose("Transition " + transition.label)

    def load_frt(self):
        for transition in self.art:
            if transition.inc_state.is_a_neighbourhood and not transition_in_set(self.frt, transition):
                self.frt.add(transition)

        if utils.VERBOSE:
            utils.print_verbose("FRT has {} transitions.".format(len(self.frt)))

            for transition in self.frt:
                utils.print_verbose("Transition " + transition.label)

    def load_urt(self):
        for transition in self.frt:
            if check_if_transition_is_only_red(transition, self.all_transitions) \
                    and not transition_in_set(self.urt, transition):
                self.urt.add(transition)

        if utils.VERBOSE:
            utils.print_verbose("URT has {} transitions.".format(len(self.urt)))

            for transition in self.urt:
                utils.print_verbose("Transition " + transition.label)

    def correct_art(self):
        corrected_art = set()

        for transition in self.art:
            if not transition_in_set(corrected_art, transition):
                corrected_art.add(transition)

        self.art = corrected_art


def check_if_transition_is_only_red(transition, all_transitions):
    for current_transition in all_transitions:
        if transition.label == current_transition.label \
                and (current_transition.transition_type == TransitionType.CORRECT or
                     current_transition.transition_type == TransitionType.NEUTRAL):
            return False

    return True
