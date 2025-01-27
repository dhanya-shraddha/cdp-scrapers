#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import Dict, List
from bs4 import BeautifulSoup
import re
import logging
from urllib.request import urlopen
from urllib.error import (
    URLError,
    HTTPError,
)

from ..legistar_utils import (
    LegistarScraper,
    CDP_VIDEO_URI,
    CDP_CAPTION_URI,
    LEGISTAR_EV_SITE_URL,
)

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class KingCountyScraper(LegistarScraper):
    def __init__(self):
        """
        kingcounty-specific implementation of LegistarScraper
        """
        super().__init__("kingcounty")

    def get_video_uris(self, legistar_ev: Dict) -> List[Dict]:
        """
        Return URLs for videos and captions parsed from kingcounty.gov web page

        Parameters
        ----------
        legistar_ev : Dict
            Data for one Legistar Event obtained from
            ..legistar_utils.get_legistar_events_for_timespan()

        Returns
        -------
        List[Dict]
            List of video and caption URI
            [{"video_uri": ..., "caption_uri": ...}, ...]
        """
        try:
            # a td tag with a certain id pattern containing url to video

            with urlopen(legistar_ev[LEGISTAR_EV_SITE_URL]) as resp:
                soup = BeautifulSoup(resp.read(), "html.parser")

        except URLError or HTTPError:
            log.debug(f"Failed to open {legistar_ev[LEGISTAR_EV_SITE_URL]}")
            return []

        try:
            # this gets us the url for the web PAGE containing the video
            # video link is provided in the window.open()command inside onclick event
            # <a id="ctl00_ContentPlaceHolder1_hypVideo"
            # data-event-id="75f1e143-6756-496f-911b-d3abe61d64a5"
            # data-running-text="In&amp;nbsp;progress" class="videolink"
            # onclick="window.open('Video.aspx?
            # Mode=Granicus&amp;ID1=8844&amp;G=D64&amp;Mode2=Video','video');
            # return false;"
            # href="#" style="color:Blue;font-family:Tahoma;font-size:10pt;">Video</a>
            extract_url = soup.find(
                "a",
                id=re.compile(r"ct\S*_ContentPlaceHolder\S*_hypVideo"),
                class_="videolink",
            )["onclick"]
            start = extract_url.find("'") + len("'")
            end = extract_url.find("',")
            video_page_url = "https://kingcounty.legistar.com/" + extract_url[start:end]

        # catch if find() didn't find video web page url (no <a id=... href=.../>)
        except KeyError:
            log.debug("No URL for video page on {legistar_ev[LEGISTAR_EV_SITE_URL]}")
            return []

        log.debug(f"{legistar_ev[LEGISTAR_EV_SITE_URL]} -> {video_page_url}")

        try:
            with urlopen(video_page_url) as resp:
                # now load the page to get the actual video url
                soup = BeautifulSoup(resp.read(), "html.parser")

        except URLError or HTTPError:
            log.error(f"Failed to open {video_page_url}")
            return []

        # source link for the video is embedded in the script of downloadLinks.
        # <script type="text/javascript">
        # var meta_id = '',
        # currentClipIndex = 0,
        # clipList = eval([8844]),
        # downloadLinks = eval([["\/\/69.5.90.100:443\/MediaVault\/Download.aspx?
        # server=king.granicus.com&clip_id=8844",
        # "http:\/\/archive-media.granicus.com:443\/OnDemand\/king\/king_e560cf63-5570-416e-a47d-0e1e13652224.mp4",null]]);
        # </script>

        video_script_text = soup.find(
            "script", text=re.compile(r"downloadLinks")
        ).string
        # Below two lines of code tries to extract video url from downLoadLinks variable
        # "http:\/\/archive-media.granicus.com:443\/OnDemand\/king\/king_e560cf63-5570-416e-a47d-0e1e13652224.mp4"
        downloadLinks = video_script_text.split("[[")[1]
        video_url = downloadLinks.split('",')[1].strip('"')
        # Cleans up the video url to remove backward slash(\)
        video_uri = video_url.replace("\\", "")
        # caption URIs are not found for kingcounty events.
        caption_uri = None
        list_uri = []
        list_uri.append({CDP_VIDEO_URI: video_uri, CDP_CAPTION_URI: caption_uri})

        if len(list_uri) == 0:
            log.debug(f"No video URI found on {video_page_url}")
        return list_uri

    def get_time_zone(self) -> str:

        """
        Return America Los Angeles (old: US/Pacific) time zone name.
        Can call find_time_zone() to find dynamically.
        Returns
        -------
        time zone name : str
            "America/Los_Angeles"
        """
        return "America/Los_Angeles"
