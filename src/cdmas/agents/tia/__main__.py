"""`cdmas-tia` entrypoint."""

from cdmas.agents._common.runner import run_agent


def main() -> None:
    run_agent("TIA")


if __name__ == "__main__":
    main()
