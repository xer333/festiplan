def test_stage_capacity_must_be_positive(client):
 r=client.post("/stages",json={
                                "festival_id":1,
                                "name":"Mainstage",
                                "capacity":0,
                                "available_equipment":[]
                               })
 assert r.status_code==422
