def test_festival_end_must_be_after_start(client):
 r=client.post("/festivals",json={
                                    "name":"Test Festival",
                                    "location":"Clisson",
                                    "start_date":"2027-06-20T10:00:00",
                                    "end_date":"2027-06-19T10:00:00"
                                  })
 assert r.status_code==400
