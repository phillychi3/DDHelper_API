import logging
import re
from typing import Any

import requests

logger = logging.getLogger("VtuberCollector")


class Vtuber:
    def extract_channel_id(self, channel_url_or_id: str) -> str:
        """
        Extract YouTube channel ID from various URL formats or handle.

        Supports:
        - Channel URLs: https://www.youtube.com/channel/UCdn5BQ06XqgXoAxIhbqw5Rg
        - Channel IDs: UCdn5BQ06XqgXoAxIhbqw5Rg
        - Handle URLs: https://www.youtube.com/@ShirakamiFubuki
        - Handle names: @ShirakamiFubuki

        Returns:
            Channel ID or original input if can't extract
        """
        if re.match(r"^UC[A-Za-z0-9_-]{22}$", channel_url_or_id):
            return channel_url_or_id
        channel_id_match = re.search(r"youtube\.com/channel/([^/?&]+)", channel_url_or_id)
        if channel_id_match:
            return channel_id_match.group(1)

        if "@" in channel_url_or_id:
            handle = channel_url_or_id
            if not handle.startswith("@"):
                handle_match = re.search(r"youtube\.com/@([^/?&]+)", channel_url_or_id)
                if handle_match:
                    handle = "@" + handle_match.group(1)
                else:
                    logger.error(f"Could not extract handle from {channel_url_or_id}")
                    return channel_url_or_id
            try:
                handle_url = f"https://www.youtube.com/{handle}"
                response = requests.get(handle_url)

                channel_id_patterns = [
                    r'"channelId":"(UC[A-Za-z0-9_-]{22})"',
                    r'"externalChannelId":"(UC[A-Za-z0-9_-]{22})"',
                    r"channelId\\x22:\\x22(UC[A-Za-z0-9_-]{22})\\x22",
                ]

                for pattern in channel_id_patterns:
                    matches = re.search(pattern, response.text)
                    if matches:
                        return matches.group(1)

                logger.error(f"Could not extract channel ID from handle {handle}")
                return channel_url_or_id

            except Exception as e:
                logger.error(f"Error getting channel ID from handle {handle}: {e}")
                return channel_url_or_id

        return channel_url_or_id

    def extract_company(self, channel_data: dict[str, Any]) -> str:
        """
        Try to extract the company from channel data.

        Args:
            channel_data: Channel data from API

        Returns:
            Company name or "Independent"
        """
        description = channel_data["snippet"]["description"].lower()

        company_keywords = {
            "hololive": "Hololive",
            "にじさんじ": "Nijisanji",
            "nijisanji": "Nijisanji",
            "vshojo": "VShojo",
            "phase connect": "Phase Connect",
            "vspo": "VSpo",
            "774inc": "774inc",
            "voms": "VOMS",
        }

        for keyword, company in company_keywords.items():
            if keyword in description:
                return company

        return "Independent"

    def _parse_count(self, count_text: str) -> int:
        """
        Parse count text from YouTube (e.g., '1.2M subscribers').

        Args:
            count_text: Text representation of count

        Returns:
            Integer value
        """
        try:
            count_text = "".join(c for c in count_text if c.isdigit() or c in [".", "K", "M", "B"])

            multiplier = 1
            if "K" in count_text:
                multiplier = 1000
                count_text = count_text.replace("K", "")
            elif "M" in count_text:
                multiplier = 1000000
                count_text = count_text.replace("M", "")
            elif "B" in count_text:
                multiplier = 1000000000
                count_text = count_text.replace("B", "")

            return int(float(count_text) * multiplier)
        except:
            return 0
