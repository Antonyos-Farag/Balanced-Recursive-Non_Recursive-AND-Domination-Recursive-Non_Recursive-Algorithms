"""Dominator — non-recursive submission (archived verbatim).

Original name: ``dominator``.  A Boyer-Moore majority vote followed by a
verification pass.  See ``docs/04-bug-hunt.md`` -> bug B8.
"""


def dominator(A):  # boyer moore majority algorithm
    N = len(A)
    candidate = None
    count = 0
    for i in range(N):
        if count == 0:
            candidate = A[i]
            count = 1
        else:
            if A[i] == candidate:
                count += 1
            else:
                count -= 1
    actual_count = 0
    index = []
    for i in range(N):
        if A[i] == candidate:
            actual_count += 1
            index.append(i)
    if actual_count > N // 2:
        return index
    else:
        return -1


if __name__ == "__main__":  # added guard: keeps `import` side-effect free
    # Example usage:
    A = [1, 2, 3, 4]
    print(dominator(A))
