"""Balanced String — non-recursive submission (archived verbatim).

Original name: ``LBS_all_longest``.  Behaviour is preserved exactly, including
the placement of the ``if distinct == 2:`` block *outside* the inner ``end``
loop.  See ``docs/04-bug-hunt.md`` -> bug B1.
"""


def LBS_all_longest(S):
    if S is None or len(S) == 0:
        return 0, []
    for ch in S:
        if not ('a' <= ch <= 'z'):
            print("Error: only lowercase letters allowed.")
            return 0, []
    n = len(S)
    longest = 0
    longest_list = []
    for start in range(n):
        freq = [0] * 26
        distinct = 0
        for end in range(start, n):
            idx = ord(S[end]) - ord('a')
            if freq[idx] == 0:
                distinct += 1
            freq[idx] += 1
            if distinct > 2:
                break
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
                    substring = ""
                    for i in range(start, end + 1):
                        substring += S[i]
                    length = end - start + 1
                    if length > longest:
                        longest = length
                        longest_list = [substring]
                    elif length == longest:
                        duplicate = False
                        for old in longest_list:
                            if old == substring:
                                duplicate = True
                                break
                        if not duplicate:
                            longest_list.append(substring)
    return longest, longest_list


if __name__ == "__main__":  # added guard: keeps `import` side-effect free
    user_input = input("Enter a lowercase string: ")
    length, longest_substrings = LBS_all_longest(user_input)
    print("\nLongest balanced substring length:", length)
    print("Balanced substrings with max length:")
    for s in longest_substrings:
        print(s)
