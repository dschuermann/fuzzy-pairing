# -*- coding: utf-8 -*-
"""
Fuzzy cryptography based on Juels & Wattenberg
Scheme "Fuzzy Commitment"
    
    :platform: Linux
    :synopsis: Fuzzy cryptography

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""
import scipy
from reedsolomon import IntegerCodec
from Crypto.Hash import SHA256
import os
import logging
# get logger
log = logging.getLogger("fuzzy_pairing")

def safe_random(length, symsize=8):
    """get random list of secified length with symbol size
    of symsize

    :param length: Length of generated list.
    :param symsize: Size of symbols :math:`2^{symsize}` bits.
    :return:  urandom_list -- The generated list.
    """
    # get raw /dev/urandom
    urandom_raw = os.urandom((2**symsize)*length)
    # normally every symbol is 256 Bit in urandom
    # we make a binary array out of it
    urandom_raw_binary = [ord(c) % (2) for c in urandom_raw]
    
    # from binary go to symbols big as defined by 2**symsize
    urandom_list = range(length)
    for i, number in enumerate(urandom_list):
        #take a block out of binary array
        start = i*symsize
        end = (i+1)*symsize
        block = urandom_raw_binary[start:end]
        # convert to string and convert to bigger number of 2**symsize
        block_string = ''.join(str(bit) for bit in block)
        urandom_list[i] = int('0b'+block_string, 2)
        
    return urandom_list

def JW_commit(x, m=15, n=20, symsize=8):
    """*Juels Wattenberg* based function to make a fuzzy commitment
    
    m,n,symsize initializes Reed-Solomon-Code with :math:`RS(q=2^{symsize},m,n)`.
                        * m -- Messages
                        * n -- Codewords
                        * Initializes Set of Codewords C
                        
    :param x: Input key x.
    :type x: list
    :param m: Parameter for Reed-Solomon-Code.
    :param n: Parameter for Reed-Solomon-Code.
    :param symsize: Parameter for Reed-Solomon-Code.
    :return: hash -- Hash of c.
    :return: delta -- Difference between x and c.
    :return: c -- Randomly generated codeword :math:`c \in C`.
    """
    
    # Reed Solomon Codeword Set C with RS(2**symsize, m, n)
    # m Messages
    # n Codewords
    # size -> 2**symsize -1
    C = IntegerCodec(n, m, symsize)
    
    
    # generate random codeword c:
    # randomize c_pre
    c_pre = safe_random(m, symsize=symsize)
    # map c_pre to codeword c to get a real codeword in C
    c = scipy.array(C.encode(c_pre)) # now size n!
    log.debug('random codeword c in C:\n'+str(c))
    log.debug('length of codeword c: '+str(len(c)))
    
    # calculate delta
    delta = (x-c) % (2**symsize)
    
    # generate SHA-256 Hash
    Hash = SHA256.new("".join(c.astype(str)))
    hash = Hash.hexdigest().split()
    
    return hash, delta, c
    
    
def JW_decommit(hash, delta, x2, m=15, n=20, symsize=8):
    """Juels Wattenberg function to decommit a fuzzy commitment
    
    m,n,symsize initializes Reed-Solomon-Code with :math:`RS(q=2^{symsize},m,n)`.
                        * m -- Messages
                        * n -- Codewords
                        * Initializes Set of Codewords C
    
    :param hash: Hash of c from Alice.
    :param delta: Difference from Alice.
    :param x2: Own input key x2. Slightly different from Alice x.
    
    :param m: Parameter for Reed-Solomon-Code.
    :param n: Parameter for Reed-Solomon-Code.
    :param symsize: Parameter for Reed-Solomon-Code.
    
    :return: c2 -- Decommited c2 
    :return: corrections -- List of corrections made by Reed-Solomon
    
    :raise: RuntimeError
    """
    
    # calculate difference x-delta
    diff = (x2-delta) % (2**symsize)
    #log.debug('Difference (codeword-delta):\n'+str(diff))
    
    # Reed Solomon Codeword Set C with RS(2**symsize, m, n)
    # m Messages
    # n Codewords
    # size -> 2**symsize -1
    C = IntegerCodec(n, m, symsize=symsize)
    
    # map diff to nearest codeword c_pre
    try:
        c_pre, corrections = C.decode(diff)
    except Exception, err:
        log.error('%s' % str(err))
        raise RuntimeError("Error in Decode of Reedsolomon Library")
    else:
        # expand codeword c_pre to get c
        c2 = scipy.array(C.encode(c_pre))
        
        # generate SHA-256 Hash
        hash_obj = SHA256.new("".join(c2.astype(str)))
        hash2 = hash_obj.hexdigest().split()
        
        # compare hash values
        if (hash == hash2):
            log.info("Decommit successfull h(c)=h(c')")
            
            #log.debug('Recovered codeword c:\n'+str(c2))
            log.debug('Reed Solomon made corrections on (positions):\n'+str(corrections))
            log.debug('Reed Solomon number of corrections: '+str(len(corrections)))
        else:
            raise RuntimeError("Hashs are not equal h(c)!=h(c')")
        
        return c2, corrections
