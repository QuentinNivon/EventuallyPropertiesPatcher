from colors import colors

VERBOSE = False


def print_warning(string):
    print(f"{colors.WARNING}Warning: {string}{colors.ENDC}")


def print_error(string):
    print(f"{colors.ERROR}Error: {string}{colors.ENDC}")


def print_verbose(string):
    print(f"{colors.OKCYAN}Debug: {string}{colors.ENDC}")


def is_an_int(str):
    try:
        int(str)
    except ValueError:
        return False

    return True


def transition_in_set(set, transition):
    for current_transition in set:
        if transition.label == current_transition.label:
            return True
    return False


# We expect a property of type INEVITABLE("A", "B", ...)
def parse_property(mcl_file):
    parsed_property = []

    with open(mcl_file) as property_file:
        property = property_file.readline()

    opening_bracket_index = property.index("(") if "(" in property else None
    closing_bracket_index = property.index(")") if ")" in property else None

    if opening_bracket_index is None or closing_bracket_index is None:
        print_error("The MCL property is badly written. It should be of the form \"INEVITABLE(\"<task1>\", "
                    "\"<task2>\", ...)\"")
        raise Exception()

    property = property[opening_bracket_index + 1: closing_bracket_index]

    try:
        index = property.index(",")
    except ValueError:
        index = -1

    while index != -1:
        label = property[0: index]
        property = property[index + 1:]
        parsed_property.append(label.replace("\"", "").strip())

        try:
            index = property.index(",")
        except ValueError:
            index = -1

    parsed_property.append(property.replace("\"", "").strip())

    return parsed_property


def transition_updates_property(property, transition, advancement):
    if advancement >= len(property) or advancement < 0:
        return False

    return property[advancement].upper() == transition.label.upper()
