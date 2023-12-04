import itertools
import sys
import time
from enum import Enum

import utils
from lts_parser import TransitionType
from utils import transition_in_set

# As this class is dealing with transitions, but consider them uniquely defined by their labels,
# and not by the tuple (inc_state, out_state, label), all operations dealing with equalities
# between Transitions (resp. EnhancedTransitions) have been rewritten manually, to consider
# that 2 transitions are equal as long as they share the same label

class Heuristic(Enum):
    MINIMAL_NUMBER_OF_CORRECTIONS = 0
    LESS_IMPACT_ON_GREEN_PART = 1


class EnhancedTransition:
    def __init__(self, transition, transitions):
        self.transition = transition
        self.reachable_incorrect_transitions = self.compute_reachable_incorrect_transitions(transitions)
        self.reachable_correct_transitions = None

    def __eq__(self, other):
        if isinstance(other, EnhancedTransition):
            return self.transition == other.transition
        return False

    def __hash__(self):
        return hash(self.transition)

    def __str__(self):
        return str(self.transition)

    def compute_reachable_incorrect_transitions(self, transitions):
        reachable_incorrect_transitions = set()
        # reachable_incorrect_transitions.add(self.transition)
        transitions_labels = {}
        visited_states = {}

        for transition in transitions:
            if transition.label == self.transition.label:
                if transition.transition_type == TransitionType.INCORRECT and not\
                        (transition.label in transitions_labels):
                    reachable_incorrect_transitions.add(transition)
                    transitions_labels[transition.label] = 1
                if not transition.transition_type == TransitionType.CORRECT:
                    self.compute_reachable_incorrect_transitions_rec(transition.out_state,
                                                                     reachable_incorrect_transitions, visited_states,
                                                                     transitions_labels)

        return reachable_incorrect_transitions

    # This function now uses a dict to store already visited states and transitions + calls itself recursively only if
    # the current transition is not a correct transition (performance issues)
    def compute_reachable_incorrect_transitions_rec(self, current_state, reachable_incorrect_transitions,
                                                    visited_states, transitions_labels):
        if current_state.label in visited_states:
            return

        visited_states[current_state.label] = 1

        for transition in current_state.out_transitions:
            if transition.transition_type == TransitionType.INCORRECT and \
                    not (transition.label in transitions_labels):
                reachable_incorrect_transitions.add(transition)
                transitions_labels[transition.label] = 1
            if not transition.transition_type == TransitionType.CORRECT:
                self.compute_reachable_incorrect_transitions_rec(transition.out_state, reachable_incorrect_transitions,
                                                                 visited_states, transitions_labels)

    def compute_reachable_correct_transitions(self, transitions):
        if self.reachable_correct_transitions is not None:
            # Avoid useless re-computations
            return

        self.reachable_correct_transitions = set()

        transitions_labels = {}
        visited_states = {}

        for transition in transitions:
            if transition.label == self.transition.label:
                if transition.transition_type == TransitionType.CORRECT and not\
                        (transition.label in transitions_labels):
                    self.reachable_correct_transitions.add(transition)
                    transitions_labels[transition.label] = 1
                if not transition.transition_type == TransitionType.INCORRECT:
                    self.compute_reachable_correct_transitions_rec(transition.out_state, visited_states,
                                                                   transitions_labels)

    # This function now uses a dict to store already visited states and transitions + calls itself recursively only if
    # the current transition is not an incorrect transition (performance issues)
    def compute_reachable_correct_transitions_rec(self, current_state, visited_states, transitions_labels):
        if current_state.label in visited_states:
            return

        visited_states[current_state.label] = 1

        for transition in current_state.out_transitions:
            if transition.transition_type == TransitionType.CORRECT and \
                    not (transition.label in transitions_labels):
                self.reachable_correct_transitions.add(transition)
                transitions_labels[transition.label] = 1
            if not transition.transition_type == TransitionType.INCORRECT:
                self.compute_reachable_correct_transitions_rec(transition.out_state, visited_states, transitions_labels)


class Patcher:
    def __init__(self, art, frt, urt, heuristic, green_transitions, red_transitions, transitions, time_bound):
        self.art = art
        self.frt = frt
        self.urt = urt
        self.transitions = transitions
        self.green_transitions = green_transitions
        self.red_transitions = red_transitions
        self.enhanced_frt = self.compute_enhanced_frt()
        self.enhanced_urt = self.compute_enhanced_urt()
        self.heuristic = heuristic
        self.time_bound = time_bound

    def compute_enhanced_frt(self):
        enhanced_frt = set()

        for transition in self.frt:
            enhanced_transition = EnhancedTransition(transition, self.transitions)
            # if not enhanced_transition_in_set(enhanced_frt, enhanced_transition):
            enhanced_frt.add(enhanced_transition)

        return enhanced_frt

    def compute_enhanced_urt(self):
        enhanced_urt = set()

        for enhanced_trans in self.enhanced_frt:
            if enhanced_trans.transition in self.urt:
                # if not enhanced_transition_in_set(enhanced_urt, enhanced_trans):
                enhanced_urt.add(enhanced_trans)

        return enhanced_urt

    def patch(self):
        if self.frt == self.urt:
            # Best case 1: no already green transition is patched
            if utils.VERBOSE:
                utils.print_verbose("Best case n°1: FRT == URT")
            possible_patches = (self.patch_red_only(self.enhanced_frt), True)
        else:
            if self.all_transitions_can_be_corrected_without_patching_green():
                # Best case 2: no already green transition is patched
                if utils.VERBOSE:
                    utils.print_verbose("Best case n°2: URT patches all red")
                possible_patches = (self.patch_red_only(self.enhanced_urt), True)
            else:
                # At least 1 already green transition will be patched
                if utils.VERBOSE:
                    utils.print_verbose("Bad case. Some already green transitions will be patched.")
                possible_patches = (self.patch_red_and_green(self.heuristic), False)

        return possible_patches

    def patch_red_only(self, combination_set):
        patched = False
        nb_transitions_to_take = 1
        patches = set()

        if utils.VERBOSE:
            utils.print_verbose("Combination set has {} elements.".format(len(combination_set)))

        # Here, we check whether patching a subset of <nb_transitions_to_take> transitions belonging to FRT
        # suffices to patch all incorrect actions in ART.
        # If so, we return this subset and all the subsets of same size having the same property.
        # Otherwise, we go to the next subset.
        # Once all subsets of size <nb_transitions_to_take> have been tested, we start a new iteration
        # with all the subsets of size <nb_transitions_to_take + 1>, until reaching the FRT subset itself.
        while (not patched) and (nb_transitions_to_take <= len(combination_set)):
            transitions_tuples = set(itertools.combinations(combination_set, nb_transitions_to_take))

            if utils.VERBOSE:
                # print(combination_set)
                # print(transitions_tuples)
                print_enhanced_transitions("\nCombination set:", combination_set)
                # print_enhanced_transitions_tuples("Transition tuples:", transitions_tuples)
                utils.print_verbose("Patched: " + str(patched))
                utils.print_verbose("Tuples size: " + str(nb_transitions_to_take))
                utils.print_verbose("Total number of red transitions: " + str(len(self.art)))

            for tuple in transitions_tuples:
                reachable_transitions = set()

                for enhanced_transition in tuple:
                    for transition in enhanced_transition.reachable_incorrect_transitions:
                        if not transition_in_set(reachable_transitions, transition):
                            reachable_transitions.add(transition)

                if utils.VERBOSE:
                    print_enhanced_transitions("Transition tuples:", tuple)
                    utils.print_verbose("Number of red transitions reachable from the current tuple: " + str(
                        len(reachable_transitions)))

                if is_transition_subset(self.art, reachable_transitions):
                    # This means that patching all the red transitions of the current tuple
                    # patches all the red transitions in ART
                    patched = True
                    # We add the current patch to the list of patches of size <nb_transitions_to_take>
                    patches.add(tuple)

            nb_transitions_to_take += 1

        return patches

    def patch_red_and_green(self, heuristic):
        if heuristic == Heuristic.MINIMAL_NUMBER_OF_CORRECTIONS:
            return self.patch_red_only(self.enhanced_frt)
        elif heuristic == Heuristic.LESS_IMPACT_ON_GREEN_PART:
            return self.patch_red_and_green_with_less_impact_on_green()
        else:
            utils.print_error("Heuristic |{}| is not implemented (yet).".format(heuristic))
            raise Exception()

    def patch_red_and_green_with_less_impact_on_green(self):
        nb_transitions_to_take = 1
        nb_already_green_transitions_repatched = sys.maxsize  # Infinite
        patches = set()

        if utils.VERBOSE:
            utils.print_verbose("Enhanced FRT has {} elements.".format(len(self.enhanced_frt)))

        start_time = time.time()

        # In this case, we need to verify all possible combinations, because
        # patching 3 transitions may have a smaller impact on the already green part
        # than patching only 1 or 2 transitions.
        # Thus, a patch is considered better if and only if its impact on the already
        # green part is strictly smaller than the impact of the current best patch
        while nb_transitions_to_take <= len(self.enhanced_frt):
            time_bound_hit = False
            executed_time = time.time() - start_time

            #TIME BOUND HITS
            if len(patches) != 0:
                if 0 < self.time_bound < executed_time:
                    break

            transitions_tuples = self.get_transitions_tuples(nb_transitions_to_take, patches)

            if transitions_tuples is None:
                break

            executed_time = time.time() - start_time

            # TIME BOUND HITS
            if len(patches) != 0:
                if 0 < self.time_bound < executed_time:
                    break

            if utils.VERBOSE:
                # print(combination_set)
                # print(transitions_tuples)
                print_enhanced_transitions("\nCombination set:", self.enhanced_frt)
                # print_enhanced_transitions_tuples("Transition tuples:", transitions_tuples)
                # print("Patched: " + str(patched))
                utils.print_verbose("Tuples size: " + str(nb_transitions_to_take))
                utils.print_verbose("Total number of red transitions: " + str(len(self.art)))

            for tuple in transitions_tuples:
                reachable_correct_transitions = set()
                reachable_incorrect_transitions = set()

                executed_time = time.time() - start_time

                # TIME BOUND HITS
                if len(patches) != 0:
                    if 0 < self.time_bound < executed_time:
                        time_bound_hit = True
                        break

                for enhanced_transition in tuple:
                    try:
                        for elem in enhanced_transition:
                            print("Current transition is iterable: " + str(elem))
                    except TypeError:
                        pass
                        #print(enhanced_transition, 'is not iterable')

                    if not isinstance(enhanced_transition, EnhancedTransition):
                        print(type(enhanced_transition))
                        print(enhanced_transition)

                    enhanced_transition.compute_reachable_correct_transitions(self.transitions)

                    for transition in enhanced_transition.reachable_correct_transitions:
                        if not transition_in_set(reachable_correct_transitions, transition):
                            reachable_correct_transitions.add(transition)

                    for transition in enhanced_transition.reachable_incorrect_transitions:
                        if not transition_in_set(reachable_incorrect_transitions, transition):
                            reachable_incorrect_transitions.add(transition)

                executed_time = time.time() - start_time

                # TIME BOUND HITS
                if len(patches) != 0:
                    if 0 < self.time_bound < executed_time:
                        time_bound_hit = True
                        break

                if utils.VERBOSE:
                    print_enhanced_transitions("Transition tuples:", tuple)
                    utils.print_verbose("Number of red transitions reachable from the current tuple: " + str(
                        len(reachable_incorrect_transitions)))
                    utils.print_verbose("Number of green transitions reachable from the current tuple: " + str(
                        len(reachable_correct_transitions)))

                if is_transition_subset(self.art, reachable_incorrect_transitions):
                    if len(reachable_correct_transitions) < nb_already_green_transitions_repatched:
                        # A better patch (i.e., correcting less already green parts) was found.
                        # Remove all patches previously found, and store the current one.
                        nb_already_green_transitions_repatched = len(reachable_correct_transitions)
                        patches.clear()
                        patches.add(tuple)
                    elif len(reachable_correct_transitions) == nb_already_green_transitions_repatched:
                        # A patch touching the same number of already green parts was found.
                        # If it has the same size, put it in the list
                        # If it is smaller, clear the list and put it in
                        # If it is bigger, ignore it
                        if len(patches) == 0 or len(next(iter(patches))) == nb_transitions_to_take:
                            patches.add(tuple)
                        elif nb_transitions_to_take < len(next(iter(patches))):
                            patches.clear()
                            patches.add(tuple)

            if time_bound_hit:
                break

            nb_transitions_to_take += 1

        return patches

    def all_transitions_can_be_corrected_without_patching_green(self):
        # Here, we check whether there exists a set of actions belonging
        # to URT which, once patched, corrects all the incorrect
        # actions belonging to ART.
        # Current method: we check if patching all actions in URT
        # correct all incorrect actions in ART.
        # Can maybe be improved by taking a smaller subset of actions
        # belonging to URT instead of URT itself (more complex).
        art_copy = deepcopy(self.art)

        for enhanced_trans in self.enhanced_frt:
            if art_copy == set():
                # All actions belonging to ART have been patched
                break

            if transition_in_set(self.urt, enhanced_trans.transition):
                # We remove all transitions patched by patching the current URT transition
                for transition in enhanced_trans.reachable_incorrect_transitions:
                    discard_transition(art_copy, transition)

        # Return True if all ART actions have been patched, False otherwise
        return art_copy == set()

    def get_transitions_tuples(self, nb_transitions_to_take, current_patches):
        if True and current_patches == set():
            return set(itertools.combinations(self.enhanced_frt, nb_transitions_to_take))
        else:
            print("V2")
            set_list = set()

            for patch in current_patches:
                copied_frt = deepcopy(self.enhanced_frt)

                for copied_transition in set(copied_frt):
                    for patch_transition in patch:
                        if patch_transition.transition.label == copied_transition.transition.label:
                            copied_frt.remove(copied_transition)

                max_nb_actions = len(patch) - 1
                min_frt_size = nb_transitions_to_take - max_nb_actions

                print(str(copied_frt))

                if len(copied_frt) < min_frt_size:
                    return None

                final_combinations = set()

                for size in range(min_frt_size, nb_transitions_to_take):
                    frt_subset = set(itertools.combinations(copied_frt, size))
                    print(str(frt_subset))
                    patch_subset = set() if min_frt_size == nb_transitions_to_take else set(itertools.combinations(patch, nb_transitions_to_take - size))
                    print(str(patch_subset))
                    combinations = frt_subset if patch_subset == set() else set(itertools.product(frt_subset, patch_subset))
                    final_combinations.update(combinations)

                if set_list == set():
                    set_list = final_combinations
                else:
                    set_list = set_list.intersection(final_combinations)

            return set_list


def deepcopy(transitions_set):
    new_set = set()

    for transition in transitions_set:
        new_set.add(transition)

    return new_set


def enhanced_transition_in_set(set, enhanced_transition):
    for current_transition in set:
        if enhanced_transition.transition.label == current_transition.transition.label:
            return True
    return False


# Used to check whether all the transitions (~ label) belonging to set a
# belong to set b.
def is_transition_subset(a, b):
    for this_transition in a:
        found = False

        for that_transition in b:
            if this_transition.label == that_transition.label:
                found = True
                break

        if not found:
            return False

    return True


def discard_transition(set, transition):
    element = None

    for current_trans in set:
        if current_trans.label == transition.label:
            element = current_trans
            break

    if element is not None:
        set.discard(element)


def print_enhanced_transitions(msg, transitions):
    string = msg + " ["
    delimiter = ""

    for enh_trans in transitions:
        string += delimiter + "S" + str(enh_trans.transition.inc_state.label) + " --" + enh_trans.transition.label \
                  + "-> S" + str(enh_trans.transition.out_state.label)

        delimiter = ", "

    string += "]"
    utils.print_verbose(string)
