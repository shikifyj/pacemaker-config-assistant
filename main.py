import argparse
from control import PacemakerConsole, HAConsole


def main():
    parser = argparse.ArgumentParser(description="vsdshaconf")
    parser.add_argument('-p', action='store_true', help='执行PacemakerConsole')
    parser.add_argument('-l', action='store_true', help='执行HAConsole')
    parser.add_argument('-v', action='store_true', help='')
    args = parser.parse_args()

    if args.p:
        PacemakerConsole()
    elif args.l:
        HAConsole()
    elif args.v:
        print('v1.0.0')
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
