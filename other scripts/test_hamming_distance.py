# -*- coding: utf-8 -*-
"""Compare two fingerprints from saved files.

    :platform: Linux
    :synopsis: Compare two fingerprints

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""
import scipy
from helper_analysis import hamming_distance
from scipy import genfromtxt

def move_right(fingerprint, steps):
    for i in range(steps):
        fingerprint = scipy.hstack((fingerprint[-1:], fingerprint[0:-1]))
    return fingerprint
    
def move_left(fingerprint, steps):
    for i in range(steps):
        fingerprint = scipy.hstack((fingerprint[1:], fingerprint[0:1]))
    return fingerprint

fingerprint1 = genfromtxt("server_fingerprint.txt")
fingerprint2 = genfromtxt("client_fingerprint.txt")


for i in range(1,10):

    print fingerprint1
    print fingerprint2    
    
    
    hdistance = hamming_distance(fingerprint1, fingerprint2)
    length = len(fingerprint1)
    percent = 100-(float(hdistance)/float(length)*100)
    
    print i, hdistance, length, percent
    
    # move it!
    fingerprint2 = move_left(fingerprint2, i)
    