from uuid import uuid4

from src.streaming.broadcaster import SubscriptionFilter


def test_empty_filter_matches_nothing():
    f = SubscriptionFilter()
    device_id = uuid4()
    assert not f.matches(device_id, "heart_rate")


def test_subscribe_all_metrics():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics=None)
    assert f.matches(device_id, "heart_rate")
    assert f.matches(device_id, "spo2")
    assert not f.matches(uuid4(), "heart_rate")


def test_subscribe_specific_metrics():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics={"heart_rate"})
    assert f.matches(device_id, "heart_rate")
    assert not f.matches(device_id, "spo2")


def test_subscribe_additive():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics={"heart_rate"})
    f.add(device_id, metrics={"spo2"})
    assert f.matches(device_id, "heart_rate")
    assert f.matches(device_id, "spo2")


def test_subscribe_all_replaces_specific():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics={"heart_rate"})
    f.add(device_id, metrics=None)
    assert f.matches(device_id, "spo2")


def test_unsubscribe_device():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics=None)
    f.remove(device_id, metrics=None)
    assert not f.matches(device_id, "heart_rate")


def test_unsubscribe_specific_metric():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics={"heart_rate", "spo2"})
    f.remove(device_id, metrics={"heart_rate"})
    assert not f.matches(device_id, "heart_rate")
    assert f.matches(device_id, "spo2")


def test_device_ids_property():
    f = SubscriptionFilter()
    d1, d2 = uuid4(), uuid4()
    f.add(d1, metrics=None)
    f.add(d2, metrics={"heart_rate"})
    assert set(f.device_ids) == {d1, d2}


def test_metrics_for_device():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics={"heart_rate", "spo2"})
    assert f.metrics_for(device_id) == {"heart_rate", "spo2"}


def test_metrics_for_device_all():
    f = SubscriptionFilter()
    device_id = uuid4()
    f.add(device_id, metrics=None)
    assert f.metrics_for(device_id) is None
