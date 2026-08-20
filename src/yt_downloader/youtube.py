import prettytable
import requests
import yt_downloader.helpers as helpers


class YTClient:
    api_key_name = "yt_api"
    api_ep = "https://youtube.googleapis.com/youtube/v3/search"
    yt_baseurl = "https://www.youtube.com/watch?v="
    print_max_len = 70

    def query_youtube(self, search_str: str, num_results: int, api_key: str) -> dict:
        """
        Function is used to query youtube for search results of given keywords.
        """
        search_str = " ".join(search_str.split())

        headers = {"Accept": "application/json"}

        query_params = {
            "part": "snippet",
            "maxResults": num_results,
            "type": "video",
            "q": search_str,
            "key": api_key,
        }

        try:
            print("Retrieving video url(s) for: ", search_str)
            response = requests.get(
                url=self.api_ep, headers=headers, params=query_params, timeout=5
            )
            response.raise_for_status()
            return response.json()
        except Exception as err:
            print(f"Error fetching video info: {err}")
            print("If persistent errors try using direct direct links instead")
            exit(-1)

    def show_ytresults_and_get_url(self, results: list) -> str:
        """
        Function prints out information using prettytable about the returned youtube resulted
            and then queries the user which video to download
        Returns:
        The url for the youtube video to download
        """
        i = 1
        table = prettytable.PrettyTable()
        table.field_names = ["Index", "Title", "Channel"]

        for result in results:
            title = result["snippet"]["title"]
            channel = result["snippet"]["channelTitle"]

            if len(title) > self.print_max_len:
                title = helpers.truncate(title, self.print_max_len)
            if len(channel) > self.print_max_len:
                channel = helpers.truncate(channel, self.print_max_len)

            table.add_row([i, title, channel])
            i += 1

        print(table)

        message = "Enter Index of Video to download:"
        invalidMessage = "Enter Correct Index"
        max_input = len(results)

        num = helpers.get_num_input(message, invalidMessage, 1, max_input, False)

        return self.yt_baseurl + YTClient.get_video_id(results, num)

    @staticmethod
    def get_video_id(results: list, index: int) -> str:
        """
        Function get_video_id returns the video id of the youtube video selected for downloading
        """
        i = 1

        for result in results:
            if index == i:
                return result["id"]["videoId"]

            i += 1

        return ""

    def get_full_url_from_video_id(self, videoID: str):
        return self.yt_baseurl + videoID
