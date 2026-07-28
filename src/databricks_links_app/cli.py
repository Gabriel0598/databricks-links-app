"""Command-line entry point for the package."""

from __future__ import annotations

import argparse

from .app import greet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Say hello")
    parser.add_argument("name", nargs="?", default="world", help="Name to greet")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    print(greet(args.name))


if __name__ == "__main__":
    main()
