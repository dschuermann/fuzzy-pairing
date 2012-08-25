# -*- coding: utf-8 -*-
"""Generate file for Dieharder

    :platform: Linux
    :synopsis: Dieharder File generation

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""
import os
import scipy
import pickle

# fingerprinting based on energy difference
import fingerprint_energy_diff

import helper_analysis

import logging
# Logging all above INFO level, output to stderr
logging.basicConfig(#format='%(asctime)s %(levelname)-8s %(message)s')
                    format='%(levelname)-8s %(message)s')
log = logging.getLogger("fuzzy_pairing")
log.setLevel(logging.DEBUG)

# open generated matrix
with file('analysis_matrix.txt', 'r') as f:
    matrix = pickle.load(f)
    
#print(matrix)


array = []
for item in matrix:
    array += [str(''.join(str(n) for n in item[1].tolist()))]  # left audio fingerprint

print(array)

with file('dieharder_input.txt', 'w') as f:
    f.write('type: b\n')
    f.write('count: '+str(len(array))+'\n')
    f.write('numbit: 512\n')
    for item in array:
        f.write(item)
        f.write('\n')
        
print('done writing file!')

