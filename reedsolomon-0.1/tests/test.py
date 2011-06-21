
"""
>>> import reedsolomon
>>> c = reedsolomon.Codec(7, 5)
>>> c.encode('abcde') == 'abcde\x94m'
True
>>> c.decode('abcde\x94m')
('abcde', [])
>>> c.decode('Abcde\x94m')
('abcde', [0])
>>> c.decode('Abcde\x94m', [0])
('abcde', [0])
>>> c.decode('Abcde\x94m', [1])
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
UncorrectableError: Corrupted input
>>> c.decode('a0cde\x94m', [1])
('abcde', [1])
>>> c.decode('a00de\x94m', [1, 2])
('abcde', [1, 2])
>>> c.decode('a000e\x94m', [1, 2, 3])
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
UncorrectableError: Too many errors or erasures in input


>>> c = reedsolomon.Codec(20, 16)
>>> original = ('abcdefghij',) * 16
>>> encoded = c.encodechunks(original)
>>> len(encoded)
20
>>> decoded, corrections = c.decodechunks(encoded)
>>> decoded == original
True
>>> corrections
[]
>>> broken = list(encoded)
>>> broken[3] = 'x' * 10
>>> decoded, corrections = c.decodechunks(broken)
>>> decoded == original
True
>>> corrections
[3]
>>> broken[14] = 'x' * 10
>>> decoded, corrections = c.decodechunks(broken, [3, 14])
>>> decoded == original
True
>>> corrections
[3, 14]
>>> broken[5] = 'x' * 10
>>> decoded, corrections = c.decodechunks(broken)
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
UncorrectableError: Too many errors or erasures in input


>>> c = reedsolomon.Codec(7, 5)
>>> encoded = c.encodechunks(['ab', 'cd', 'ef', 'gh', 'ijklm'])
Traceback (most recent call last):
  File "<string>", line 1, in ?
ValueError: The input strings have unequal length
>>> encoded = c.encodechunks(['ab', 'cd', 'ef', 'gh', 'ij'])
>>> encoded == ('ab', 'cd', 'ef', 'gh', 'ij', '[\x07', '&\xcf')
True
>>> decoded, corrections = c.decodechunks(encoded)
>>> corrections
[]
>>> decoded
('ab', 'cd', 'ef', 'gh', 'ij')
>>> delta = reedsolomon.xor('ab', 'xy')
>>> np1 = c.updatechunk(0, delta, 5, encoded[5])
>>> np2 = c.updatechunk(0, delta, 6, encoded[6])
>>> new_encoded = ('xy', 'cd', 'ef', 'gh', 'ij', np1, np2)
>>> expect_encoded = c.encodechunks(['xy', 'cd', 'ef', 'gh', 'ij'])
>>> new_encoded == expect_encoded
True


>>> reedsolomon.xor('abcCBA', 'bcdDCB') == '\x03\x01\x07\x07\x01\x03'
True
>>> reedsolomon.xor('a', 'bc')
Traceback (most recent call last):
  File "<stdin>", line 1, in ?
ValueError: The strings have unequal length


>>> c = reedsolomon.IntegerCodec(7, 5)
>>> c.encode([1, 2, 3, 4, 5])
[1, 2, 3, 4, 5, 113, 227]
>>> c.decode([1, 2, 3, 4, 5, 113, 227])
([1, 2, 3, 4, 5], [])
>>> c.decode([1, 99, 3, 4, 5, 113, 227])
([1, 2, 3, 4, 5], [1])

"""

def _test():
    import doctest, test
    return doctest.testmod(test)

if __name__ == "__main__":
    failed, attempts = _test()
    print '%d/%d passed' % (attempts - failed, attempts)
