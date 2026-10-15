"""Dominator — recursive submission (archived verbatim).

Original names: ``find_dominator_recursive`` and ``find_dominator_indices``.
Behaviour is preserved exactly.  See ``docs/04-bug-hunt.md`` -> bugs B10-B14.
"""


def find_dominator_recursive(A, left, right):
    if left == right:
        return (A[left], [left])
    if left + 1 == right:
        if A[left] == A[right]:
            return (A[left], [left, right])
        return (None, [])
    mid = (left + right) // 2
    left_candidate, left_indices = find_dominator_recursive(A, left, mid)
    right_candidate, right_indices = find_dominator_recursive(A, mid + 1, right)

    if left_candidate == right_candidate and left_candidate is not None:
        count = 0
        indices = []
        for i in range(left, right + 1):
            if A[i] == left_candidate:
                count += 1
                indices.append(i)
        if count > (right - left + 1) // 2:
            return (left_candidate, indices)
        return (None, [])
    left_count = sum(1 for i in range(left, right + 1) if A[i] == left_candidate) if left_candidate is not None else 0
    if left_candidate is not None:
        count = 0
        indices = []
        for i in range(left, right + 1):
            if A[i] == left_candidate:
                count += 1
                indices.append(i)
        if count > (right - left + 1) // 2:
            return (left_candidate, indices)

    if right_candidate is not None:
        count = 0
        indices = []
        for i in range(left, right + 1):
            if A[i] == right_candidate:
                count += 1
                indices.append(i)
        if count > (right - left + 1) // 2:
            return (right_candidate, indices)

    return (None, [])


def find_dominator_indices(A):
    if len(A) == 0:
        return []
    value, indices = find_dominator_recursive(A, 0, len(A) - 1)
    if indices:
        return indices
    return []


if __name__ == "__main__":  # added guard: keeps `import` side-effect free
    A = [2]
    print(find_dominator_indices(A))  # Output: [0, 2, 4, 6, 7] (index of dominator element 3)
