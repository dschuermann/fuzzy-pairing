# -*- coding: utf-8 -*-
"""Test for Fingerprint based on energy diffs

    :platform: Linux
    :synopsis: Test for Fingerprint based on energy diffs

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""

from helper_analysis import hamming_distance
from helper_audio import load_mono
 

base = "/home/ds1/Projekte/Bachelorarbeit/Program/recordings/"

# fingerprinting based on energy difference
import fingerprint_energy_diff

import logging
# Logging all above INFO level, output to stderr
logging.basicConfig(#format='%(asctime)s %(levelname)-8s %(message)s')
                    format='%(levelname)-8s %(message)s')
log = logging.getLogger("fuzzy_pairing")
log.setLevel(logging.DEBUG)


# load channels:
left_channel, samplerate = load_mono(base+'1.5_3/high/music5.wav')
right_channel, samplerate = load_mono(base+'1.5_3/high/music1.wav')


# fingerprint energy diff
fingerprint_left = fingerprint_energy_diff.get_fingerprint(left_channel, samplerate)
fingerprint_right = fingerprint_energy_diff.get_fingerprint(right_channel, samplerate)

print repr(fingerprint_left)
print repr(fingerprint_right)

# calculate hamming distance between fingerprints
distance = hamming_distance(fingerprint_left, fingerprint_right)
length = len(fingerprint_left)
print length, distance
print('Correlation %: '+str(1-float(distance)/float(length)))

