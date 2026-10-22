def test_publish_unknown_festival_returns_404(client):
 assert client.post("/festivals/999/publish").status_code==404
