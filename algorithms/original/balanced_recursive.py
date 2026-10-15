"""Balanced String — recursive submission (archived verbatim).

Original name: ``LBS`` with helpers ``TryStart`` and ``TryEnd``.
Behaviour is preserved exactly.  See ``docs/04-bug-hunt.md`` -> bugs B3-B7.
"""


def LBS(S):
    S = S.lower()

    n = len(S)
    longest = 0
    best_list = []

    longest, best_list = TryStart(S, n, 0, longest, best_list)
    return longest, best_list


def TryStart(S, n, start, longest, best_list):
    if start == n:
        return longest, best_list

    freq = [0] * 26
    distinct = 0

    longest, best_list = TryEnd(S, n, start, start, freq, distinct, longest, best_list)

    return TryStart(S, n, start + 1, longest, best_list)


def TryEnd(S, n, start, end, freq, distinct, longest, best_list):
    if end == n:
        return longest, best_list

    if not S[end].isalpha():
        return longest, best_list

    index = ord(S[end]) - ord('a')

    if freq[index] == 0:
        distinct += 1

    freq[index] += 1


    if distinct > 2:
        return longest, best_list


    if distinct == 2:
        firstFreq = -1
        secondFreq = -1

        for f in freq:
            if f > 0:
                if firstFreq == -1:
                    firstFreq = f
                elif secondFreq == -1:
                    secondFreq = f


        if firstFreq != -1 and secondFreq != -1 and firstFreq == secondFreq:
            substring = S[start:end + 1]
            length = end - start + 1

            if length > longest:
                longest = length
                best_list = [substring]
            elif length == longest and substring not in best_list:
                best_list.append(substring)

    return TryEnd(S, n, start, end + 1, freq[:], distinct, longest, best_list)


if __name__ == "__main__":  # added guard: keeps `import` side-effect free
    user_input = input("Enter any string (uppercase allowed): ")

    length, substrings = LBS(user_input)

    print("\nBalanced substring length:", length)
    print("All longest balanced substrings:")
    for s in substrings:
        print(s)
