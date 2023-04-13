from knowledge_mapper.utils import extract_variables


def test_extract_variables_1():
    assert extract_variables("?a ?b ?c . ?a a <something> .") == {"a", "b", "c"}
