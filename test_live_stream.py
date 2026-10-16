from app.services import live


def test_live_publish_delivers_new_item_once():
    queue = live.subscribe()
    item = {
        "id": 987654,
        "source": "Test Source",
        "title": "A newly ingested test headline",
    }
    try:
        live.publish(item)
        received = queue.get_nowait()
        assert received == item
        assert queue.empty()
    finally:
        live.unsubscribe(queue)


def test_unsubscribed_queue_does_not_receive_items():
    queue = live.subscribe()
    live.unsubscribe(queue)

    live.publish({"id": 987655, "title": "Should not be delivered"})

    assert queue.empty()
