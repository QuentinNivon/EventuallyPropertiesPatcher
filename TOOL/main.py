import os
import sys
import utils
import time
import subprocess

from command_line_parser import Parser, Argument
from counterexamples_generator import CounterexamplesGenerator
from lts_parser import LtsParser
from lts_writer import LtsWriter
from patcher import Patcher, Heuristic
from transitions_loader import TransitionsLoader
from truncator import Truncator, Truncation
from verifier import Verifier

TEST = False
DAUT_FILE_ALREADY_EXISTS = 1
BCG_FILE_ALREADY_EXISTS = 2
BCG_GENERATION_FAILED = 3
DAUT_GENERATION_FAILED = 4
BAD_USAGE = 5


def launch_patcher(cmd_line_parser, conversion_time):
    # Parse LTS
    print("Parsing LTS...")
    parse_start = time.time()
    ltsParser = LtsParser()
    ltsParser.parse(cmd_line_parser.get(Argument.LTS))
    parse_end = time.time()
    parse_time = parse_end - parse_start
    print("Parsing LTS: DONE ({}s)".format(parse_time))

    if TEST:
        if commandLineParser.get(Argument.CLTS) is not None:
            # Compute CLTS
            print("Parsing CLTS...")
            compute_clts_start = time.time()
            cltsParser = LtsParser()
            cltsParser.parse(cmd_line_parser.get(Argument.CLTS))
            initial_state = None
            compute_clts_end = time.time()
            compute_clts_time = compute_clts_end - compute_clts_start
            print("Parsing CLTS: DONE ({}s)".format(compute_clts_time))
        else:
            # Compute CLTS
            print("Computing CLTS...")
            compute_clts_start = time.time()
            generator = CounterexamplesGenerator(ltsParser, cmd_line_parser.get(Argument.MCL_PROPERTY))
            cltsParser = generator.generate()
            initial_state = None
            compute_clts_end = time.time()
            compute_clts_time = compute_clts_end - compute_clts_start
            print("Computing CLTS: DONE ({}s)".format(compute_clts_time))
    else:
        # Compute CLTS
        print("Computing CLTS...")
        compute_clts_start = time.time()
        generator = CounterexamplesGenerator(ltsParser, cmd_line_parser.get(Argument.MCL_PROPERTY))
        cltsParser = generator.generate()
        initial_state = None
        compute_clts_end = time.time()
        compute_clts_time = compute_clts_end - compute_clts_start
        print("Computing CLTS: DONE ({}s)".format(compute_clts_time))

    if not TEST:
        for state in cltsParser.states:
            if state.label == 0:
                initial_state = state
                break

        if initial_state is not None:
            if utils.VERBOSE:
                print(initial_state.stringify(set(), 0))
            verifier = Verifier(initial_state)
            print("Generated CLTS is semantically correct: " + str(verifier.verify()))
        else:
            utils.print_error("No CLTS was generated. Exiting.")
            exit(1)

    # Write generated CLTS to file
    print("Writing CLTS to file...")
    write_start = time.time()
    ltsWriter = LtsWriter(cmd_line_parser.get(Argument.LTS), cltsParser, cmd_line_parser.get(Argument.OVERRIDE), False)
    ltsWriter.generate_aut()
    write_end = time.time()
    write_time = write_end - write_start
    print("Writing CLTS to file: DONE ({}s)".format(write_time))

    # Compute ART, FRT, URT
    print("Computing ART, FRT, UFRT...")
    compute_subsets_start = time.time()
    transitionsLoader = TransitionsLoader(cltsParser.transitions)
    transitionsLoader.load_subsets()
    compute_subsets_end = time.time()
    compute_subsets_time = compute_subsets_end - compute_subsets_start
    print("Computing ART, FRT, UFRT: DONE ({}s)".format(compute_subsets_time))

    # Patch
    print("Computing patches...")
    patch_start = time.time()
    patcher = Patcher(transitionsLoader.art, transitionsLoader.frt, transitionsLoader.urt,
                      Heuristic.LESS_IMPACT_ON_GREEN_PART, cltsParser.green_transitions,
                      cltsParser.red_transitions, cltsParser.transitions, Argument.TIME_BOUND)
    result = patcher.patch()
    patch_end = time.time()
    patch_time = patch_end - patch_start
    patches = result[0]
    clean_patch = result[1]
    print("Computing patches: DONE ({}s)".format(patch_time))

    # Generate truncated CLTS (remove green part)
    print("Truncating CLTS...")
    truncate_start = time.time()
    truncator = Truncator(cltsParser, cmd_line_parser.get(Argument.OVERRIDE), cmd_line_parser.get(Argument.MCL_PROPERTY))
    #truncator.truncate(Truncation.FULL_AFTER_LIVENESS)
    #ltsWriter = LtsWriter(cmd_line_parser.get(Argument.LTS), cltsParser, cmd_line_parser.get(Argument.OVERRIDE), True)
    #ltsWriter.generate_aut()
    truncate_end = time.time()
    truncate_time = truncate_end - truncate_start
    print("Truncating CLTS: DONE ({}s)".format(truncate_time))

    if patches is None or patches == set():
        print("\nNo patch could be found.")
    else:
        if len(patches) == 1:
            print("\n1 patch was found for the current specification.")

            if not clean_patch:
                utils.print_warning("Applying this patch will necessarily impact one or many already correct "
                                    "parts of the specification.")

            print("Patch found:\n")
        else:
            print("\n{} patches were found for the current specification.".format(len(patches)))

            if not clean_patch:
                utils.print_warning("Applying one of these patches will necessarily impact\none or many "
                                    "already correct parts of the specification.")

            print("Patches found:\n")

        patch_index = 1

        for patch in patches:
            patch_str = "- Patch n°{}:".format(patch_index)
            patch_str += "\n    - Transitions to patch: "
            separator = ""
            for enhanced_trans in patch:
                patch_str += separator + enhanced_trans.transition.label
                separator = " + "
            patch_index += 1
            print(patch_str)

    print("--------------------------------------------------")
    print("Process took {}s to execute.\n    - LNT conversion took {}s\n    - Parsing took {}s\n    - Computing CLTS "
          "took {}s\n    - Writing CLTS to file took {}s\n    - Computing ART, FRT, URT took {}s\n    - Computing "
          "possible patches took {}s\n    - Truncating CLTS took {}s"
          .format((parse_time + compute_clts_time + write_time + compute_subsets_time + patch_time) * 1000,
                  conversion_time * 1000,
                  parse_time * 1000,
                  compute_clts_time * 1000,
                  write_time * 1000,
                  compute_subsets_time * 1000,
                  patch_time * 1000,
                  truncate_time * 1000
                  )
          )

    # for state in ltsParser.states:
    # print(str(state))
    # print("\n")

    # print(str(ltsGraph))


# The script expects as input a file in .fautx (full autx), meaning
# that the green part of the LTS is not truncated (as done by CLEAR).
if __name__ == '__main__':
    commandLineParser = Parser(sys.argv)
    commandLineParser.compute_args()

    if commandLineParser.get(Argument.VERBOSE):
        utils.VERBOSE = True

    process_should_stop = False

    # If LNT specification has been given, transform it to deterministic LTS
    if commandLineParser.get(Argument.LNT) is not None:
        print("Converting LNT to AUT...")
        conversion_start = time.time()
        lnt_path = commandLineParser.get(Argument.LNT)
        lnt_filename = lnt_path[lnt_path.rfind('/') + 1:].replace(".lnt", "")
        # Call external script "lnt_to_aut_dir.sh" to transform .lnt file to .daut (Deterministic AUT = LTS)
        completed_process = subprocess.run([
            os.getcwd() + '/lnt_to_aut_dir.sh',                 # Process to run
            commandLineParser.get(Argument.WORKING_DIRECTORY),  # 1st argument: Working directory
            lnt_filename,                                       # 2nd argument: LNT process
        ], stdout=subprocess.DEVNULL)                           # Put stdout on /dev/null to avoid subprocess output
        # Replace the LNT by the LTS in the command line parser
        commandLineParser.set(Argument.LNT, None)
        lts_path = commandLineParser.get(Argument.WORKING_DIRECTORY) + "/" + lnt_filename + ".daut"
        commandLineParser.set(Argument.LTS, lts_path)
        conversion_end = time.time()
        conversion_time = conversion_end - conversion_start

        if completed_process.returncode != 0:
            if completed_process.returncode == DAUT_FILE_ALREADY_EXISTS:
                utils.print_warning("A .daut file corresponding to the given LNT specification is already present in "
                                    "the working directory. It will be used by the patcher.")
            elif completed_process.returncode == BCG_FILE_ALREADY_EXISTS:
                utils.print_error("A .bcg file corresponding to an intermediate file of the LNT conversion has been "
                                  "found in the working directory. Please remove it from the working directory and "
                                  "try again.")
                process_should_stop = True
            elif completed_process.returncode == BCG_GENERATION_FAILED:
                utils.print_error("The generation of the .bcg intermediate file has failed. Please check the result "
                                  "of the CADP command \"lnt.open <your_file>.lnt generator <your_file>.bcg\"")
                process_should_stop = True
            elif completed_process.returncode == DAUT_GENERATION_FAILED:
                utils.print_error("The generation of the .daut file has failed. Please check the result of the CADP "
                                  "commands \"bcg_open <your_file>.bcg reductor -weaktrace "
                                  "<your_file>_weaktraced.bcg\" and \"bcg_io <your_file>_weaktraced.bcg "
                                  "<your_file>_weaktraced.aut\" and try again.")
                process_should_stop = True
            elif completed_process.returncode == BAD_USAGE:
                utils.print_error("This should never happen. Please contact the team.")
                process_should_stop = True
        print("Conversion DONE. ({}s)".format(conversion_time))
    else:
        conversion_time = 0

    if not process_should_stop:
        launch_patcher(commandLineParser, conversion_time)
