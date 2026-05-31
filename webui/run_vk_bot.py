from __future__ import annotations

import argparse
import logging

from app.config import get_settings
from app.services.vk_bot import VkBotSettings, VkLongPollBot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Lakmus VK bot template")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Enable message_new in Bots Long Poll settings before starting the bot",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    vk_settings = VkBotSettings.from_app_settings(get_settings())
    bot = VkLongPollBot(vk_settings)

    if args.setup:
        logging.info("Enabling message_new in Bots Long Poll settings")
        bot.setup()

    bot.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
