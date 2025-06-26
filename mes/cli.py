import curses
from mes.main import main


def run():
    curses.wrapper(main)


if __name__ == "__main__":
    run()
