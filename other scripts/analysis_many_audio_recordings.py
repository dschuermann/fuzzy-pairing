# -*- coding: utf-8 -*-
"""Analyze many recorded audio files.

    :platform: Linux
    :synopsis: Analyze
    
.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""

from helper_analysis import hamming_distance
from helper_audio import load_stereo, load_mono
import os
import scipy
import pickle

# fingerprinting based on energy difference
import fingerprint_energy_diff

import logging
# Logging all above INFO level, output to stderr
logging.basicConfig(#format='%(asctime)s %(levelname)-8s %(message)s')
                    format='%(levelname)-8s %(message)s')
log = logging.getLogger("fuzzy_pairing")
log.setLevel(logging.DEBUG)


path = "/home/ds1/Projekte/Fuzzy Pairing Paper/Versuche Audiodateien/"


matrix = list()
      
# get all files in all subdirectories etc.
for root, dirs, files in os.walk(path):
    for name in files:
        filename = os.path.join(root, name)
        print filename
       
        print "current file is: " + name
        mono_channel, samplerate = load_mono(filename)
        
        # fingerprint energy diff
        fingerprint = fingerprint_energy_diff.get_fingerprint(mono_channel, samplerate)
        
        # you can add more analysis using helper_analysis here
        # and write the results in the matrix for further analyzing

        matrix.append([filename,fingerprint])

print matrix

# save it with pickle, can later be analyzed
with file('analysis_matrix.txt', 'wr') as f:
    pickle.dump(matrix, f)

