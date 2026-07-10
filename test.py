#!/bin/env python3
import os
import subprocess
import sys
import shlex
import coloredlogs, logging

'''-COLORED PRINT------------'''
import sys

colors_table = {
    'BLACK':   [ '30', '40' ],
    'RED':     [ '31', '41' ],
    'GREEN':   [ '32', '42' ],
    'YELLOW':  [ '33', '43' ],
    'BLUE':    [ '34', '44' ],
    'MAGENTA': [ '35', '45' ],
    'CYAN':    [ '36', '46' ],
    'WHITE':   [ '37', '47' ],
    'DEFAULT': [ '39', '49' ],
    'RESET':   [ '00', '00' ],
}

def set_color(fg: str = 'DEFAULT', bg: str = 'DEFAULT', file=sys.stdout):
    bg = bg.upper()
    fg = fg.upper()
    if bg not in colors_table:
        raise ValueError(f'{bg} is not a valid color!, we only support 8 colors only!')
    if fg not in colors_table:
        raise ValueError(f'{fg} is not a valid color!, we only support 8 colors only!')
    print(f"\033[{colors_table[fg][0]};{colors_table[bg][1]}m", file=file, end='')


def cprint(fg: str, bg: str, msg: str, file=sys.stdout, *args, **kwargs):
    set_color(fg, bg, file)
    print(msg, file=file, **kwargs)
    set_color(file=file)
'''-------------------------'''

CMD_LEVEL = 15
logging.addLevelName(CMD_LEVEL, "CMD")

class MyLogger(logging.Logger):
    def cmd(self, msg, *args, **kwargs):
        if self.isEnabledFor(CMD_LEVEL):
            self._log(CMD_LEVEL, msg, args, **kwargs)


logging.setLoggerClass(MyLogger)

logger = logging.getLogger('test')
logger.setLevel(logging.DEBUG)

coloredlogs.install(
    level='DEBUG', 
    fmt='%(name)s [%(levelname)s]: %(message)s',
    level_styles={
        'cmd': {'color': 'cyan'},  # Color for CMD level
        'debug': {'color': 'white'},
        'info': {'color': 'green'},
        'warning': {'color': 'yellow'},
        'error': {'color': 'red'},
        'critical': {'color': 'magenta'},
    },
    field_styles={
        'name': {'color': 'cyan'},
        'levelname': {'bold': True},
    }
)

# TODO: Implement or Use a third-party diff-ing library

## Substitutable values; These values are substituted with the following values if found in BUILD_CMD or RUN_CMD

# - {test_name}  - name of the test.
# - {src_suffix} - suffix of the source files. (excluding the .)

# BUILD_CMD will be the command run when the `build` subcommand is ran.
BUILD_CMD="NOT SET"
# Same as the BUILD_CMD but run when the `run` command is ran.
RUN_CMD="NOT SET"
# The name of the directory all the tests live in. (Will chdir to this)
TESTS_DIR="NOT SET"
# Suffix of the source files the build command iw (if there is a . prefix, it will be removed
SRC_SUFFIX="NOT SET"

def get_env_variables():
    global BUILD_CMD, RUN_CMD, TESTS_DIR, SRC_SUFFIX
    BUILD_CMD = os.environ["BUILD_CMD"] if "BUILD_CMD" in os.environ else "NOT SET"
    RUN_CMD = os.environ["RUN_CMD"] if "RUN_CMD" in os.environ else "NOT SET"
    TESTS_DIR = os.environ["TESTS_DIR"] if "TESTS_DIR" in os.environ else "NOT SET"
    SRC_SUFFIX = os.environ["SRC_SUFFIX"] if "SRC_SUFFIX" in os.environ else "NOT SET"
    SRC_SUFFIX = SRC_SUFFIX.removeprefix(".")
    # SRC_SUFFIX = os.environ["SRC_SUFFIX"] if "SRC_SUFFIXsuffix" in os.environ else "NOT SET"


def get_cmd_substituted(cmd, tests, current_test):
    assert current_test in tests, "The test that you passed is not in the tests map!"
    cmd = cmd.replace("{test_name}", tests[current_test].name)
    cmd = cmd.replace("{src_suffix}", SRC_SUFFIX)

    return cmd

def check_crucial_envvar(var, var_name):
    if var == "NOT SET":
        logger.error(f"`{var_name}` environment variable not set! please provide a value and run again!")
        exit(1)


def expect_output(expected_name: str, expected: str, got: str):
    print(f"Expected {expected_name}: ")
    print(">>>")
    cprint("green", "default", expected)
    print(">>>")
    print("But got: ")
    print("<<<")
    cprint("red", "default", got)
    print("<<<")


class Test:
    def __init__(self, name):
        self.name = name
        self.d = {
            "stdin": "",
            "expected_stdout": "",
            "expected_stderr": "",
            "expected_returncode": -1,

            "build_stdin": "",
            "expected_build_stdout": "",
            "expected_build_stderr": "",
            "expected_build_returncode": -1,
        }


        self.load_expected()

    def __repr__(self):
        return f'''
        stdin: {self.d['stdin']},
        expected_stdout: {self.d['expected_stdout']},
        expected_stderr: {self.d['expected_stderr']},
        expected_returncode: {self.d['expected_returncode']},

        build_stdin: {self.d['build_stdin']},
        expected_build_stdout: {self.d['expected_build_stdout']},
        expected_build_stderr: {self.d['expected_build_stderr']},
        expected_build_returncode: {self.d['expected_build_returncode']},
        '''

    def save_expected(self):
        filename: str = f"{self.name}.test"
        f = open(filename, "w")
        def write_section(section: str):
            f.write(f"[{section}]\n")
            f.write(f"{self.d[section]}\n")

        write_section("stdin")
        write_section("expected_stdout")
        write_section("expected_stderr")
        write_section("expected_returncode")

        write_section("build_stdin")
        write_section("expected_build_stdout")
        write_section("expected_build_stderr")
        write_section("expected_build_returncode")
        f.close()

    def load_expected(self):
        filename: str = f"{self.name}.test"
        if not os.path.exists(filename):
            with open(filename, "w") as file:
                pass
            return
        with open(filename, "r") as f:
            current_section: str = ""
            for line in f.readlines():
                line = line.rstrip('\n')
                if len(line) <= 0: continue
                # print(f"LINE: `{line}`") continue
                if line[0] == '[':
                    section: str = line.removeprefix('[').removesuffix(']')
                    # print(f"Got section `{section}`")
                    current_section = section
                else:
                    data = line
                    if current_section not in self.d:
                        logger.error(f"{current_section} is not a valid section!")
                        exit(1)
                    else:
                        if current_section.find("returncode") != -1:
                            try:
                                self.d[current_section] = int(data)
                            except ValueError:
                                logger.error(f"{data} is not a valid returncode bruh!")
                                exit(1)
                        else:
                            self.d[current_section] += data + "\n"

    def get_expected_filename(self, name):
        if name not in [ "in", "out", "err", "code", "build.in", "build.out", "build.err", "build.code" ]:
            raise Exception("Please pass a valid name")

        return f".{self.name}.{name}.expected"

    def get_build_stdin_list(self):
            build_input_array = self.d["build_stdin"].split(sep=' ')
            for i in range(len(build_input_array)-1, -1, -1):
                if len(build_input_array[i]) <= 0:
                    build_input_array.pop(i)
            return build_input_array

    def get_stdin_list(self):
            input_array = self.stdin.split(sep=' ')
            for i in range(len(input_array)-1, -1, -1):
                if len(input_array[i]) <= 0:
                    input_array.pop(i)
            return input_array

def usage(program: str):
    logger.info(f"Usage: {program} <subcmd> [flags]")

# NOTE: We named this hhelp because help is a builtin python function
def hhelp():
    print('''
    Subcommands:
        help            - Prints this help message.
        build           - Builds all the tests.
        run             - Runs all the tests.
        record          - Records the expected behaviour of all the tests.
        record_build    - Records the expected build behaviour of all the tests.
        list            - Lists all the tests.

    Flags:
        -h             - Same as the help subcommand.
        -V             - Verbose output.
        -x             - Stop on first error.
        -t <test_name> - Specify the test to run/build/etc.
          ''')

def main():
    program = sys.argv.pop(0)

    if len(sys.argv) <= 0:
        logger.error("Please provide at least one subcommand!")
        usage(program)
        hhelp()
        exit(1)


    # FLAG_VALUES
    verbose_output = False
    stop_on_error  = False

    subcmds = []

    test_name = None

    while len(sys.argv) > 0:
        arg = sys.argv.pop(0)

        if arg.startswith('-') or arg.startswith('/'):
            flag_with_prefix = arg
            flag = flag_with_prefix[1:]
            if flag == 'h':
                hhelp()
                exit(0)
            elif flag == 'V':
                verbose_output = True
            elif flag == 'x':
                stop_on_error = True
            elif flag == 't':
                if len(sys.argv) <= 0:
                    logger.error(f"Please provide the name of the test after {flag_with_prefix}")
                    exit(1)
                test_name = sys.argv.pop(0)
            else:
                logger.error(f"Invalid flag '{flag}'")
                exit(1)
        else:
            subcmds.append(arg)

    if len(subcmds) <= 0:
        logger.error("Please provide at least one subcommand!")
        usage(program)
        hhelp()
        exit(1)

    get_env_variables()

    check_crucial_envvar(TESTS_DIR, "TESTS_DIR")
    check_crucial_envvar(SRC_SUFFIX, "SRC_SUFFIX")

    os.chdir(TESTS_DIR)
    if verbose_output: logger.info(f"Changed cwd to {os.getcwd()}")

    tests = {}

    for e in sorted(os.listdir(os.getcwd())):
        if not e.endswith("." + SRC_SUFFIX): continue
        base_name = e.removesuffix("." + SRC_SUFFIX)
        if not tests.get(base_name):
            tests[base_name] = Test(base_name)
            # print(f"TEST: {tests[base_name]}")

    # User wanted to test a specific test_name
    if test_name != None:
        # Remove suffix
        test_name = test_name.removesuffix(SRC_SUFFIX)
        if test_name not in tests:
            logger.error(f"{test_name} is not a valid test!")
            exit(1)

        new_tests = tests.copy()
        for t in tests:
            if t != test_name:
                new_tests.pop(t)
        tests = new_tests

    # print(f"BUILD_CMD: {BUILD_CMD}")
    # print(f"RUN_CMD: {RUN_CMD}")
    # print(f"TESTS_DIR: {TESTS_DIR}")
    # print(f"SRC_SUFFIX: {SRC_SUFFIX}")

    for subcmd in subcmds:
        total_tests_count = len(tests)
        current_test_id = 0
        passing_tests_count = 0

        if subcmd == "list":
            logger.info("Tests: ")
            for t in tests:
                logger.info(f"-> {t}")
        elif subcmd == "help":
            hhelp()
            exit(0)
        elif subcmd == "build":
            check_crucial_envvar(BUILD_CMD, "BUILD_CMD")
            cprint('green', 'default', f'----- [BUILD] -----')
            for test_name in tests:
                cprint('green', 'default', f'+ Building {test_name}.{SRC_SUFFIX} [{current_test_id+1}/{total_tests_count}]...')
                current_test_id += 1
                test = tests[test_name]

                if test.d["expected_build_returncode"] == -1:
                    logger.warning(f"Test doesn't have any expected build returncode!")
                    logger.warning(f"Please record the expected build behaviour of the test using the 'record_build' subcommand!")
                    cprint('yellow', 'default', f"[SKIPPING]...")
                    if stop_on_error: exit(1)
                    continue

                cmd = shlex.split(get_cmd_substituted(BUILD_CMD, tests, test_name))
                build_stdin_list = test.get_build_stdin_list()
                if len(build_stdin_list) > 0: cmd.extend(build_stdin_list)
                # vlog(verbose_output, f"[CMD] {cmd}")
                res = subprocess.run(cmd, capture_output = True, text = True)
                if res.returncode != 0:
                    m = ''
                    if res.stderr:
                        m += f"{res.stderr}"
                    logger.error(f"[FAILED] {m}")

                    if stop_on_error: exit(1)
                    else: continue
                else:
                    failed = False
                    if res.stdout != test.d["expected_build_stdout"]:
                        cprint('red', 'default', f'[FAILED]')
                        expect_output("stdout", test.d["expected_build_stdout"], res.stdout)
                        failed = True
                        if stop_on_error: exit(1)
                    if res.stderr != test.d["expected_build_stderr"]:
                        cprint('red', 'default', f'[FAILED]')
                        expect_output("stderr", test.d["expected_build_stderr"], res.stderr)
                        failed = True
                        if stop_on_error: exit(1)
                    if not failed:
                        passing_tests_count += 1
                        cprint('green', 'default', "[PASS] ")
                    o = False
                    if verbose_output and res.stdout:
                        print(f"{res.stdout}")
                        o = True
                    if verbose_output and res.stderr:
                        print(f"{res.stderr}")
                        o = True
                    if not o: print('')

        elif subcmd == "run":
            check_crucial_envvar(RUN_CMD, "RUN_CMD")
            cprint('green', 'default', f'----- [RUN] -----')
            for test_name in tests:
                cprint('green', 'default', f'+ Running {test_name} [{current_test_id+1}/{total_tests_count}]...')
                current_test_id += 1
                test = tests[test_name]

                res = None
                try:
                    cmd = shlex.split(get_cmd_substituted(RUN_CMD, tests, test_name))
                    # vlog(verbose_output, f"[CMD] {cmd}")
                    res = subprocess.run(cmd, capture_output = True, text = True)
                except Exception as e:
                    logger.error(f"Failed to run ./{test_name}: {e}")
                    if stop_on_error: exit(1)
                    else: continue

                if test.expected_returncode == -1:
                    logger.warning(f"Test doesn't have any expected returncode!")
                    logger.warning(f"Please record the expected behaviour of the test using the 'record' subcommand!")

                if res.stdout != test.expected_stdout:
                    cprint('red', 'default', f'[FAILED]')
                    expect_output("stdout", test.expected_stdout, res.stdout)
                    if stop_on_error: exit(1)
                    else: continue
                passing_tests_count += 1
                cprint('green', 'default', '[PASS]')

            cprint(f"green", "default", f"PASSED {passing_tests_count}/{total_tests_count}")
        elif subcmd == "record":
            check_crucial_envvar(RUN_CMD, "RUN_CMD")
            print(f'----- [RECORD] -----')
            for test_name in tests:
                cprint(f"green", "default", f"+ Recording expected behaviour for '{test_name}'...")
                test = tests[test_name]

                cmd = shlex.split(get_cmd_substituted(RUN_CMD, tests, test_name))
                stdin_list = test.get_stdin_list()
                if len(stdin_list) > 0: cmd.extend(stdin_list)
                # vlog(verbose_output, f"[CMD] {cmd}")
                res = subprocess.run([f"./{test_name}"], capture_output = True, text = True)

                print(f"stdout: {res.stdout}")
                print(f"stderr: {res.stderr}")
                print(f"returncode: {res.returncode}")

                prompt_msg = "Record current behaviour as the expected one? [y/N]"
                ans = input(prompt_msg)

                if ans.lower() == "y":
                    tests[test_name].d["expected_stdout"] = res.stdout
                    tests[test_name].d["expected_stderr"] = res.stderr
                    tests[test_name].d["expected_returncode"] = res.returncode
                    tests[test_name].save_expected()
                    cprint("green", "default", '[SUCCESS] Recorded expected behaviour')
                else:
                    cprint('yellow', 'default', '[SKIP]')
        elif subcmd == "record_build":
            check_crucial_envvar(BUILD_CMD, "BUILD_CMD")
            cprint("green", "default", f'----- [RECORD_BUILD] -----')
            for test_name in tests:
                cprint(f"green", "default", f"+ Recording expected build behaviour for '{test_name}'...")
                test = tests[test_name]

                if len(test.d["build_stdin"]) > 0:
                    logger.info(f"Test already has build_input '{test.d['build_stdin']}'...")
                    ans = input("Do you want to change the build_input? [y/N]")
                    if ans.lower() == 'y':
                        test.d["build_stdin"] = input("What is the input passed? ")
                    else:
                        cprint('yellow', 'default', '[SKIP]')
                        continue
                else:
                    test.d["build_stdin"] = input("What is the input passed? ")

                cmd = shlex.split(get_cmd_substituted(BUILD_CMD, tests, test_name))
                build_stdin_list = test.get_build_stdin_list()
                if len(build_stdin_list) > 0: cmd.extend(build_stdin_list)
                # vlog(verbose_output, f"[CMD] {cmd}")
                res = subprocess.run(cmd, capture_output = True, text = True)

                print(f"stdout: {res.stdout}")
                print(f"stderr: {res.stderr}")
                print(f"returncode: {res.returncode}")

                prompt_msg = "Record current build behaviour as the expected one? [y/N]"
                ans = input(prompt_msg)

                if ans.lower() == "y":
                    tests[test_name].d["expected_build_stdout"] = res.stdout
                    tests[test_name].d["expected_build_stderr"] = res.stderr
                    tests[test_name].d["expected_build_returncode"] = res.returncode
                    tests[test_name].save_expected()
                    cprint('green', 'default', '[SUCCESS] Recorded expected behaviour')
                else:
                    cprint('yellow', 'default', '[SKIP]')

        else:
            logger.error(f"Invalid subcommand '{subcmd}'")
            exit(1)

if __name__ == "__main__":
    main()
