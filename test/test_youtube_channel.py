from youtube_live import Youtube_webscrap


def test_channel_data():
    channel_url = "https://www.youtube.com/@stringflowers"

    mock_youtube_live = Youtube_webscrap()
    test = mock_youtube_live.get_channel_info(channel_url)
    print(test)

    assert test["channel_id"] == channel_url
