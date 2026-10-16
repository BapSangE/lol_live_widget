"""Run the widget against the public LoL Esports schedule and stats feed."""

import argparse

from run_lck_replay import main

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--league", default="worlds", choices=["worlds", "lck", "lpl", "lec", "lcs"]
    )
    args = parser.parse_args()
    main(live=True, league=args.league)
