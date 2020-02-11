import argparse
import logging
import logging.config
from bot.app import run

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--loglevel",
        action="store",
        dest="loglevel",
        default="DEBUG",
        choices=["DEBUG", "INFO", "WARNINGS", "ERROR"],
        help="Log level",
    )

    args = parser.parse_args()
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=args.loglevel,
    )

    run()
