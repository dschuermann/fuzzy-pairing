# -*- coding: utf-8 -*-
"""Test for JW Fuzzy Commitment

    :platform: Linux
    :synopsis: Test for JW Fuzzy Commitment

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""


import crypto_fuzzy_jw
import scipy

def random_fingerprints(length, difference, symsize=1):
    """generates random fingerprints with length
    and difference in percent like 0.3"""
    # generate randomized fingerprints
    fingerprint1 = scipy.random.randint(0, 2**symsize, length)
    fingerprint2 = fingerprint1.copy()

    # invert specific random positions to get slightly differing fingerprint2
    invert_positions = scipy.random.randint(0, length, size=length*difference)
    for i in invert_positions:
        fingerprint2[i] = not fingerprint2[i]
    
    return fingerprint1, fingerprint2
    


# fingerprint binary
finger1, finger2 = random_fingerprints(512, 0.3, symsize=1)





print('fingerprint 1:\n'+str(finger1))
print('fingerprint 2:\n'+str(finger2))

print("---------------------------")
print("Bob:\n")

# doing commit
a, d, c = crypto_fuzzy_jw.JW_commit(finger1, m=256, n=512, symsize=10)
print("private codeword c:\n"+str(c))
print("Blob:\n"+str(a)+"\n"+str(d))


print("\nAlice:\n")

# doing decommit
c2, corr = crypto_fuzzy_jw.JW_decommit(a, d, finger2, m=256, n=512, symsize=10)
print("recovered codeword c:\n"+str(c2))
print("made corrections on:\n"+str(corr))