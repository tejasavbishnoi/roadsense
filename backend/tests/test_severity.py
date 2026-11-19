from app import severity


def det(label, conf=0.9, area=0.02):
    return {"label": label, "confidence": conf, "area_ratio": area, "box": [0, 0, 0.1, 0.1]}


def test_empty_road_is_good():
    assert severity.score([]) == 0
    assert severity.assess([], 0.25) == {"score": 0, "level": "Good", "counts": {}, "total": 0}


def test_pothole_worse_than_crack():
    assert severity.score([det("pothole")]) > severity.score([det("longitudinal_crack")])


def test_bigger_damage_scores_higher():
    assert severity.score([det("pothole", area=0.08)]) > severity.score([det("pothole", area=0.001)])


def test_score_is_bounded():
    many = [det("pothole", area=0.2) for _ in range(100)]
    assert 0 <= severity.score(many) <= 100


def test_confidence_filter_and_counts():
    dets = [det("pothole", 0.9), det("pothole", 0.1), det("transverse_crack", 0.5)]
    result = severity.assess(dets, min_conf=0.25)
    assert result["counts"] == {"pothole": 1, "transverse_crack": 1}
    assert result["total"] == 2


def test_levels():
    assert severity.level(0) == "Good"
    assert severity.level(20) == "Fair"
    assert severity.level(50) == "Poor"
    assert severity.level(95) == "Critical"
    assert severity.level(100) == "Critical"
