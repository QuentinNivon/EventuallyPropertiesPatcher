import os
from enum import Enum
from os.path import isdir, isfile

from utils import print_warning, print_error, is_an_int


class Argument(Enum):
    LTS = 0
    MCL_PROPERTY = 1
    VERBOSE = 2
    OVERRIDE = 3
    LNT = 4
    WORKING_DIRECTORY = 5
    CLTS = 6
    TIME_BOUND = 7


class Parser:
    def __init__(self, arguments):
        self.arguments_map = {
            Argument.LTS: None,
            Argument.VERBOSE: False,
            Argument.OVERRIDE: False,
            Argument.MCL_PROPERTY: None,
            Argument.LNT: None,
            Argument.WORKING_DIRECTORY: None,
            Argument.TIME_BOUND: -1
        }
        self.sys_args = arguments

    def compute_args(self):
        for i in range(1, len(self.sys_args)):
            arg = self.sys_args[i]

            if is_lts(arg):
                if self.arguments_map[Argument.LTS] is not None:
                    print_warning("An LTS file has already been specified. It will be overwritten by the current one.")
                self.arguments_map[Argument.LTS] = arg
            elif is_time_bound(arg):
                self.arguments_map[Argument.TIME_BOUND] = parse_time_bound(arg)
            elif is_verbose(arg):
                self.arguments_map[Argument.VERBOSE] = True
            elif is_override(arg):
                self.arguments_map[Argument.OVERRIDE] = True
            elif is_mcl_property(arg):
                if self.arguments_map[Argument.MCL_PROPERTY] is not None:
                    print_warning("An MCL file has already been specified. It will be overwritten by the current one.")
                self.arguments_map[Argument.MCL_PROPERTY] = arg
            elif is_lnt(arg):
                if self.arguments_map[Argument.LNT] is not None:
                    print_warning("An LNT file has already been specified. It will be overwritten by the current one.")
                self.arguments_map[Argument.LNT] = arg
            elif is_dir(arg):
                if self.arguments_map[Argument.WORKING_DIRECTORY] is not None:
                    print_warning("A working directory has already been specified. It will be overwritten by the "
                                  "current one.")
                self.arguments_map[Argument.WORKING_DIRECTORY] = arg
            else:
                print_warning("Argument |{}| was not recognized. It has been ignored.".format(arg))

        if not arguments_validated(self.arguments_map):
            print_error("LTS/LNT file or MCL property are missing or invalid. Please try again.")
            raise Exception()

        self.compute_working_directory()

    def get(self, argument):
        if argument not in self.arguments_map:
            print_error("Argument |{}| was not recognized.".format(argument))
            raise Exception()

        return self.arguments_map[argument]

    def set(self, key, value):
        if key not in self.arguments_map:
            print_error("Argument |{}| was not recognized.".format(key))
            raise Exception()

        self.arguments_map[key] = value

    def compute_working_directory(self):
        file_path = self.get(Argument.LNT) if (self.get(Argument.LNT) is not None) else self.get(Argument.LTS)
        last_slash_index = file_path.rfind('/')
        working_directory = file_path[0:last_slash_index]
        self.arguments_map[Argument.WORKING_DIRECTORY] = working_directory


def is_verbose(arg):
    return arg == "-v" \
           or arg == "-verbose" \
           or arg == "--v" \
           or arg == "--verbose"


def is_override(arg):
    beautiful_arg = arg.lower()

    return beautiful_arg == "-f" \
           or beautiful_arg == "-override" \
           or beautiful_arg == "--f" \
           or beautiful_arg == "--override" \


def is_lts(arg):
    return arg.endswith(".aut") or arg.endswith(".daut")


def is_lnt(arg):
    return arg.endswith(".lnt")


def is_mcl_property(arg):
    return arg.endswith(".mcl")


def is_dir(arg):
    return arg.endswith("/") or "." not in arg

def is_time_bound(arg):
    return arg.startswith("-bound=")


def arguments_validated(arguments):
    if arguments.get(Argument.WORKING_DIRECTORY) is not None:
        if not isdir(arguments.get(Argument.WORKING_DIRECTORY)):
            print_error("|{}| is not a directory.".format(arguments.get(Argument.WORKING_DIRECTORY)))
            return False
        compute_other_args(arguments)

    if arguments.get(Argument.LNT) is not None:
        arguments[Argument.LTS] = None

    if not (xor(arguments.get(Argument.LTS), arguments.get(Argument.LNT))
            and arguments[Argument.MCL_PROPERTY] is not None):
        print_error("Either an LTS + an LNT were specified or the MCL property is missing.")
        return False

    if arguments.get(Argument.LNT) is not None:
        spec_is_file = isfile(arguments.get(Argument.LNT))
    else:
        spec_is_file = isfile(arguments.get(Argument.LTS))

    files_are_valid = spec_is_file and isfile(arguments.get(Argument.MCL_PROPERTY))

    if not files_are_valid:
        print_error("The LNT/LTS file or the MCL file are not valid files.")

    return files_are_valid


def compute_other_args(arguments):
    working_directory = arguments.get(Argument.WORKING_DIRECTORY)
    lnt_files = set()
    aut_files = set()
    mcl_files = set()
    autx_files = set()

    for file in os.listdir(os.fsencode(working_directory)):
        filename = os.fsdecode(file)

        if filename.endswith(".lnt"):
            lnt_files.add(filename)
        elif filename.endswith(".aut") or filename.endswith(".daut"):
            aut_files.add(filename)
        elif filename.endswith(".mcl"):
            mcl_files.add(filename)
        elif filename.endswith(".autx"):
            autx_files.add(filename)

    if len(lnt_files) == 1:
        lnt_file = next(iter(lnt_files))
        current_lnt_file = arguments.get(Argument.LNT)

        if current_lnt_file is not None:
            print_warning("The specified LNT file will be overwritten by the one found in the given working directory.")

        arguments[Argument.LNT] = working_directory + "/" + lnt_file
    else:
        print_warning("{} LNT files were found in the current directory. None of them was used.".format(len(lnt_files)))

    if len(aut_files) == 1:
        aut_file = next(iter(aut_files))
        current_aut_file = arguments.get(Argument.LTS)

        if current_aut_file is not None:
            print_warning("The specified LTS file will be overwritten by the one found in the given working directory.")

        arguments[Argument.LTS] = working_directory + "/" + aut_file
    else:
        print_warning("{} AUT/DAUT files were found in the current directory. None of them was used.".format(
            len(aut_files)))

    if len(mcl_files) == 1:
        mcl_file = next(iter(mcl_files))
        current_mcl_file = arguments.get(Argument.MCL_PROPERTY)

        if current_mcl_file is not None:
            print_warning("The specified MCL property will be overwritten by the one found in the given working "
                          "directory.")

        arguments[Argument.MCL_PROPERTY] = working_directory + "/" + mcl_file
    else:
        print_warning("{} MCL files were found in the current directory. None of them was used.".format(len(mcl_files)))

    if len(autx_files) == 1:
        autx_file = next(iter(autx_files))
        arguments[Argument.CLTS] = working_directory + "/" + autx_file

def parse_time_bound(arg):
    bound = arg[arg.index('-bound=') + len('-bound='):]

    if not is_an_int(bound):
        raise RuntimeError("Bound {} is not an integer value.".format(bound))

    return int(bound)

def xor(arg1, arg2):
    return (arg1 is not None and arg2 is None) or (arg1 is None and arg2 is not None)
