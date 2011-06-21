# -*- coding: utf-8 -*-
"""Functions used by server and client

    :platform: Linux
    :synopsis: Functions used by server and client

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""
import scipy
import logging
# get logger
log = logging.getLogger("fuzzy_pairing")
import fingerprint_energy_diff
log.setLevel(logging.DEBUG)


def generate_key_for_aes(codeword):
    """take the codeword generated with Fuzzy Cryptography,
    and reformat it to use it as AES key.
    
    AES keys:
        * AES uses 256 Bit=32 Bytes as Keys
        * Every character in AES key is 8 Bits
    
    Codewords:
        * Codewords are 512 symbols long
        * Every symbol has numbers from 0 to :math:`2^{10}-1` (0 to 1023)
        
    Mapping Codewords to AES keys:
        * Add every 16 numbers blocks
        * Mapping symbols to numbers from 0 to :math:`2^{8}-1` (0 to 255) with modulo
    
    :param codeword: 512 symbols long codeword list
    :type codeword: list
    :return: 32 byte key for AES
    """
    
    # add 16 numbers blocks to build a array with 32 numbers
    key_new = range(32)
    for i, number in enumerate(key_new):
        for j in range(i*16, (i+1)*16):
            key_new[i] += codeword[j]
    
    # make every number a number between 0 and 2**8
    # -> a 8 bit long number
    for i, number in enumerate(key_new):
        key_new[i] = number % 2**8
    
    log.debug('AES key array:\n'+repr(key_new))
    
    # make a character string out of it
    key_string = ''
    for number in key_new:
        key_string += chr(number)
    
    log.debug('AES key string:\n'+repr(key_string))
    
    return key_string
    
def move_data_right(data, steps):
    """move data to the right and fill rest with zeros
    
    :param data: chunks of data
    :param steps: steps to move
    :type steps: int
    :return: data
    """
    number = steps*100
    data = scipy.hstack(([0]*number, data[0:-number]))
    return data
    
def move_data_left(data, steps):
    """move data to the left and fill rest with zeros
    
    :param data: chunks of data
    :param steps: steps to move
    :type steps: int
    :return: data
    """
    number = steps*100
    data = scipy.hstack((data[number:], [0]*number))
    return data
    
def get_possible_fingerprints(recording_data, recording_samplerate):
    """generate many fingerprints varying in time
    
    :param recording_data: complete recording data
    :param recording_samplerate: samplerate of recording
    :return: many fingerprints
    """
    fingerprint = fingerprint_energy_diff.get_fingerprint(recording_data, recording_samplerate)
    possible_fingerprints = [fingerprint]
    # correct 0,20 seconds in time (0,20*44100=~8800) -> 88*100 data chunks!
    n = 176 # -> 0,4 seconds
    for i in range(1, n):
        log.debug('Generating possible fingerprint '+str(i)+' of '+str(n))
        # move 100 data chunks to left and build fingerprint
        data_left = move_data_left(recording_data, i)
        possible_fingerprints += [fingerprint_energy_diff.get_fingerprint(data_left, recording_samplerate)]
        # move 100 data chunks to right and build fingerprint
        data_right = move_data_right(recording_data, i)
        possible_fingerprints += [fingerprint_energy_diff.get_fingerprint(data_right, recording_samplerate)]

    return possible_fingerprints
