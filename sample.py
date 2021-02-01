import random

import click


@click.command()
@click.option(
    "--number", type=int, default=10, help="Number of lines to sample (default 10)"
)
@click.argument("input", type=click.File("r"), required=True)
def main(input, number):
    """
    Randomly sample some lines from the file INPUT.
    """
    # ignore blank lines
    lines = [line.strip() for line in input.readlines() if line.strip()]
    number = min(number, len(lines))
    random.shuffle(lines)
    for i in range(number):
        print(lines[i])


if __name__ == "__main__":
    main()
