import os.path

from utils import print_warning


class LtsWriter:
    def __init__(self, full_filename, lts_parser, override, truncated):
        filename_with_path = compute_filename_and_path(full_filename)
        self.filename = filename_with_path[0].replace(".daut", "") + ("_truncated" if truncated else "")
        self.path = filename_with_path[1]
        self.full_autx_filename = self.path + "/" + self.filename + ".autx"
        self.lts_parser = lts_parser
        self.override = override

    def generate_aut(self):
        if not self.override and os.path.exists(self.full_autx_filename):
            print_warning("The file |{}.autx| already exists in the current directory and the overwriting permission "
                          "has not been given.".format(self.filename))
            return

        with open(self.full_autx_filename, "w") as full_lts:
            full_lts.write("des ({}, {}, {})\n".format(
                self.lts_parser.initial_state,
                self.lts_parser.nb_transitions,
                self.lts_parser.nb_states)
            )

            for transition in self.lts_parser.transitions:
                full_lts.write("({}{}, \"{}\":{}, {})\n".format(
                    transition.inc_state.label,
                    ":N:" + transition.inc_state.color.value if transition.inc_state.is_a_neighbourhood else "",
                    transition.label.upper(),
                    transition.transition_type.value,
                    transition.out_state.label
                ))


def compute_filename_and_path(full_filename):
    slash_index = full_filename.rfind('/')
    path = full_filename[:slash_index]
    filename = full_filename[slash_index + 1:]

    return [filename, path]
