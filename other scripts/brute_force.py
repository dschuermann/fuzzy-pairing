# -*- coding: utf-8 -*-
"""Brute Force Attack on Delta with different fingerprints
    
    :platform: Linux
    :synopsis: Brute Force Attack

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""
import scipy
import crypto_fuzzy_jw
import logging
from itertools import product


# Logging all above INFO level, output to stderr and file
logging.basicConfig(filename='brute_force.log',
                    format='%(levelname)-8s %(message)s')
log = logging.getLogger("brute_force")
log.setLevel(logging.INFO)

log_pairing = logging.getLogger("fuzzy_pairing")
log_pairing.setLevel(logging.CRITICAL) # no unimportant logs from crypto_fuzzy_jw!

hash = ['9b75c0e991387c9022d25c7a22ffe7d0a1ad3d8ffb55a40ccfbe7705cfb6000b']
delta = scipy.genfromtxt("client_delta.txt")
successfull_fingerprint = scipy.genfromtxt("client_fingerprint.txt")
m=152
n=512
symsize=10
# correcting 512-152/2=180 errors


position = 0
for fingerprint_tuple in product([0,1], repeat=n):
    # using product method from
    # http://docs.python.org/library/itertools.html
    # to get all possible binary lists
    fingerprint = list(fingerprint_tuple)
    
    position += 1
    
    if (position % 1000) == 0:
        log.info("Now on fingerprint position "+str(position)+"\nwith fingerprint "+str(fingerprint))

    try:
        # trying to decommit
        private_key, corr = crypto_fuzzy_jw.JW_decommit(hash, delta, fingerprint, m, n, symsize)
    except Exception, err:
        pass # don't show extra error
        #log.error('%s' % str(err))
    else:
        # if hash is the same accept key agreement,
        # test is in JW_decommit, try fails when not!
        # return True for accepted connection
        log.info('Broken!!!\nPrivate Key:\n'+str(private_key))
