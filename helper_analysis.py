# -*- coding: utf-8 -*-
"""
Helper Functions

    :platform: Linux
    :synopsis: Helper Functions

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""

import scipy
import matplotlib.pyplot as plot

import logging
# get logger
log = logging.getLogger("fuzzy_pairing")


def hamming_distance(fingerprint1, fingerprint2):
    """Number of ciphers that are different in ``fingerprint1``
    compared to ``fingerprint2``
    
    .. note: Length of fingerprints must be the same
    
    :param fingerprint1: List with numbers
    :param fingerprint2: List with numbers
    """
    distance = 0
    for i, cipher in enumerate(fingerprint1):
        if (cipher != fingerprint2[i]):
            distance += 1
    return distance
    
def absolute_distance(fingerprint1, fingerprint2):
    """Calculate absolute distance
    
    .. note: Length of fingerprints must be the same
    
    :param fingerprint1: List with numbers
    :param fingerprint2: List with numbers
    """
    absolute_distance = 0
    for i, cipher in enumerate(fingerprint1):
        absolute_distance += scipy.fabs(cipher-fingerprint2[i])
    return absolute_distance

def hamming_weight(fingerprint):
    """Number of ciphers in fingerprint that are not 0
    
    :param fingerprint: List with numbers
    """
    weight = 0
    for cipher in fingerprint:
        if (cipher == 0):
            weight += 1
    return weight