from knowledge_mapper.utils import match_bindings

def test_match_bindings_1():
    source = [
        {"a": "a1", "b": "b1", "c": "c1"},
        {"a": "a2", "b": "b2", "c": "c2"},
        {"a": "a3", "b": "b3", "c": "c3"},
    ]
    query = [
        {"a": "a1"},
    ]

    result = match_bindings(query, source)

    expected = [
        {"a": "a1", "b": "b1", "c": "c1"},
    ]

    assert dict_list_eq(expected, result)

def test_match_bindings_2():
    source = [
        {"a": "a1", "b": "b1", "c": "c1"},
        {"a": "a2", "b": "b2", "c": "c2"},
        {"a": "a3", "b": "b3", "c": "c3"},
    ]
    query = [
        {"a": "a1"},
        {"a": "a2"},
    ]

    result = match_bindings(query, source)

    expected = [
        {"a": "a1", "b": "b1", "c": "c1"},
        {"a": "a2", "b": "b2", "c": "c2"},
    ]

    print(result)

    assert dict_list_eq(expected, result)


def dict_list_eq(l1, l2):
    sorted_l1 = sorted(sorted(d.items()) for d in l1)
    sorted_l2 = sorted(sorted(d.items()) for d in l2)
    return sorted_l1 == sorted_l2
