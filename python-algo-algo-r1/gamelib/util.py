import sys
from time import time_ns


BANNER_TEXT = "---------------- Starting Your Algo --------------------"


def get_command():
    """Gets input from stdin

    """
    try:
        ret = sys.stdin.readline()
    except EOFError:
        # Game parent process terminated so exit
        debug_write("Got EOF, parent game process must have died, exiting for cleanup")
        exit()
    if ret == "":
        # Happens if parent game process dies, so exit for cleanup, 
        # Don't change or starter-algo process won't exit even though the game has closed
        debug_write("Got EOF, parent game process must have died, exiting for cleanup")
        exit()
    return ret

def send_command(cmd):
    """Sends your turn to standard output.
    Should usually only be called by 'GameState.submit_turn()'

    """
    sys.stdout.write(cmd.strip() + "\n")
    sys.stdout.flush()

def debug_write(*msg):
    """Prints a message to the games debug output

    Args:
        msg: The message to output

    """
    #Printing to STDERR is okay and printed out by the game but doesn't effect turns.
    sys.stderr.write(", ".join(map(str, msg)).strip() + "\n")
    sys.stderr.flush()


def timer(func):
    def inner(*args, **kwargs):
        t1 = time_ns()
        ret = func(*args, **kwargs)
        t2 = time_ns()
        debug_write(f"Execution time of <{func.__name__}>: {(t2-t1)/10**6} ms")
        return ret
    return inner