def match_bindings(query: list[dict], source: list[dict]) -> list:
    matches = []
    for s in source:
        for q in query:
            q_matches = True
            for k, v in q.items():
                if not (k in s and s[k] == v):
                    q_matches = False
                    break
            if q_matches:
                matches.append(s.copy())
                break
    return matches
