"""`cdmas-aca` entrypoint."""

from cdmas.agents._common.runner import run_agent


def main() -> None:
    run_agent("ACA")


if __name__ == "__main__":
    main()
