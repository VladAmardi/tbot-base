import traceback
import sys
from typing import Callable


def boolean_input(question, default=None):
    result = None
    try:
        result = input("%s " % question)
    except KeyboardInterrupt:
        print('')
        exit(0)

    if not result and default is not None:
        return default
    while len(result) < 1 or result[0].lower() not in "yn":
        result = input("Please answer yes or no: ")
    return result[0].lower() == "y"


def catch_and_print_exceptions(exit_after: bool = False, callback_after: Callable = None):
    def __wrapper_func(_func):
        def _wrapper(*args, **kwargs):
            # noinspection PyBroadException
            try:
                return _func(*args, **kwargs)
            except BaseException as e:
                output = traceback.format_exc().split("\n")
                print("\n".join(output[0:1]+output[3:]), file=sys.stderr)
                sys.stderr.flush()
            if callback_after is not None and callable(callback_after):
                callback_after()
            if exit_after:
                sys.exit(1)

        return _wrapper

    return __wrapper_func
