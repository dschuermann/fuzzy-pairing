
"""
Results from a Pentium M at 1.7 GHZ, compiled with '-O2 -march=pentium3':
<Codec(n=10, k=8, symsize=8, gfpoly=391, fcr=112, prim=11, variant='char')>
encoded 10.00 MiB in 0.88 s (11.35 MiB/s)
decoded 12.50 MiB in 0.72 s (17.37 MiB/s)

"""

import reedsolomon
import time

MiB = 1 << 20

def main():
    c = reedsolomon.Codec(10, 8)

    data = (''.join([chr(i) for i in range(256)])) * 40961
    chunksize, remainder = divmod(len(data), c.k)
    if remainder:
        chunksize += 1
    chunks = []
    for i in range(c.k):
        chunk = data[chunksize * i : chunksize * (i + 1)]
        if len(chunk) < chunksize:
            chunk += '\0' * (chunksize - len(chunk))
        chunks.append(chunk)
    start = time.time()
    encoded = c.encodechunks(chunks)
    end = time.time()
    assert len(encoded) == c.n

    encoded_bytes = float(sum([len(s) for s in chunks]))
    encode_time = end - start

    start = time.time()
    decoded, corrections = c.decodechunks(encoded)
    end = time.time()
    assert not corrections
    assert len(decoded) == c.k
    assert (''.join(decoded))[:len(data)] == data

    decoded_bytes = float(sum([len(s) for s in encoded]))
    decode_time = end - start

    print c
    print 'encoded %0.2f MiB in %0.2f s (%0.2f MiB/s)' % (
        encoded_bytes / MiB, encode_time, encoded_bytes / MiB / encode_time)
    print 'decoded %0.2f MiB in %0.2f s (%0.2f MiB/s)' % (
        decoded_bytes / MiB, decode_time, decoded_bytes / MiB / decode_time)

if __name__ == '__main__':
    main()
