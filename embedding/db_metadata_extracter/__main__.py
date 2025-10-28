import logging
from .config import AppConfig
from .presentation import CLI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)


def main():
    config = AppConfig.from_env()
    cli = CLI(config)
    cli.run()


if __name__ == "__main__":
    main()

