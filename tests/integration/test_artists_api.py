def test_artist_name_must_be_a_string(client):
 r=client.post("/artists",json={
                                    "name":123,
                                    "genre":"Metal",
                                    "required_equipment":[]
                                })
 assert r.status_code==422
