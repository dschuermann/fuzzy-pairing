# -*- coding: utf-8 -*-
"""
Fuzzy Pairing Server Implementation
    
    :platform: Linux
    :synopsis: Server Implementation

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""
import logging
import scipy

import crypto_fuzzy_jw
import fingerprint_energy_diff

from Crypto.Cipher import AES

from twisted.spread import pb
from twisted.internet import reactor

from helper_audio_recording import record_at_time
from helper_audio import load_stereo, load_mono

from helper_check_ntp import time_in_sync
from helper_implementation import generate_key_for_aes, get_possible_fingerprints

from helper_analysis import hamming_distance

# Logging all above INFO level, output to stderr
logging.basicConfig(#format='%(asctime)s %(levelname)-8s %(message)s')
                    format='%(levelname)-8s %(message)s')
log = logging.getLogger("fuzzy_pairing")
log.setLevel(logging.DEBUG)
    
def main():
    # start server
    reactor.listenTCP(4200, pb.PBServerFactory(PairingServer()))
    reactor.run()

class PairingServer(pb.Root):
    def __init__(self):
        """Initialize PairingServer object
        """
        self.fingerprint = None
        self.delta = None
        self.hash = None
        self.private_key = None
        self.recording_data = None
        self.recording_samplerate = None
        self.recording_use_file = False
        self.recording_file = 'server_recording.wav'
        self.rs_code_m = 152
        self.rs_code_n = 512
        self.rs_code_symsize = 10
        self.check_ntp = False
        self.debug = False # Using this means NO security!
        self.debug_file = "minimals.txt"

    
    def remote_connection(self, device_id):
        """2. Bob accepts or denies connection request
        
        Bob gets ``device_id`` from Alice. Bob tests for correct
        id and checks NTP time.
        
        :param device_id: String like "Alice"
        :type device_id: str
        """
        log.info('2. Bob accepts or denies connection request')
        
        # very very simple implementation to test device_id
        if device_id == "Alice":
            if self.check_ntp:
                # check NTP
                if not time_in_sync():
                    log.info('Local time not in sync with NTP')
                    return False
                else:
                    log.info('NTP time ok')
            return True
        else:
            return False
            
    def remote_recording(self, start_time):
        """5. remote recording
        (4 and 5 are called synchron at ``start_time``)
        
        Function waits until ``start_time`` and then starts recording
        
        :param start_time: Absolute time when recording should start
        :type start_time: int
        """
        log.info('5. remote recording')
        
        if self.recording_use_file:
            # load recording from file
            self.recording_data, self.recording_samplerate = load_mono(self.recording_file)

            return True
        else:
            # start recording at start_time
            self.recording_data, self.recording_samplerate = record_at_time("server.wav", 7, start_time)

            return True

        
    def remote_agreement(self, hash, delta):
        """8. Key Agreement on Server
        generates fingerprint and decommits
        using received ``hash`` and ``delta``
        
        :param hash: SHA-512 Hash of codeword c
        :type hash: str
        :param delta: difference
        :type delta: list
        """
        log.info('8. Key Agreement on Server')
        
        #===============================================================================
        # Fingerprinting and Fuzzy Cryptography
        #===============================================================================       
        # generate fingerprint, not used see possible fingerprints
        self.fingerprint = fingerprint_energy_diff.get_fingerprint(self.recording_data, self.recording_samplerate)
        
        # save fingerprint for debugging
        scipy.savetxt("server_fingerprint.txt", self.fingerprint)

        log.debug('Bob fingerprint:\n'+str(self.fingerprint))
        
        # get possible fingerprints
        possible_fingerprints = get_possible_fingerprints(self.recording_data, self.recording_samplerate)
                
        for fingerprint in possible_fingerprints:
            try:
                # trying to decommit
                self.private_key, corr = crypto_fuzzy_jw.JW_decommit(hash, delta, fingerprint, m=self.rs_code_m, n=self.rs_code_n, symsize=self.rs_code_symsize)
            except Exception, err:
                log.error('%s' % str(err))
                
            else:
                # if hash is the same accept key agreement,
                # test is in JW_decommit, try fails when not!
                # return True for accepted connection
                return True
        
        # if every fingerprint fails to decommit pairing fails
        return False
        
    def remote_agreement_debug(self, fingerprint_debug, hash, delta):
        """THIS IS A DEBUG FUNCTION
        using the fingerprint from the client
        Using this means NO security!
        
        8. Key Agreement on Server
        generates fingerprint and decommits
        using received ``hash`` and ``delta``
        
        :param hash: SHA-512 Hash of codeword c
        :type hash: str
        :param delta: difference
        :type delta: list
        """
        log.info('8. Key Agreement on Server')
        
        #===============================================================================
        # Fingerprinting and Fuzzy Cryptography
        #===============================================================================       
        # generate fingerprint, not used see possible fingerprints
        self.fingerprint = fingerprint_energy_diff.get_fingerprint(self.recording_data, self.recording_samplerate)
        
        # save fingerprint for debugging
        scipy.savetxt("server_fingerprint.txt", self.fingerprint)

        log.debug('Bob fingerprint:\n'+str(self.fingerprint))
        
        # get possible fingerprints
        possible_fingerprints = get_possible_fingerprints(self.recording_data, self.recording_samplerate)
        
        # DEBUG
        length = len(fingerprint_debug)
        
        distances = []
        
        for fingerprint in possible_fingerprints:
            # calculate hamming distance between fingerprints
            distance = hamming_distance(fingerprint, fingerprint_debug)
            print('Distance: '+str(distance)+' of '+str(length))
            print('Correlation percentage: '+str(1-float(distance)/float(length)))
            distances += [distance]
        
        min_distance = min(distances)
        min_correlation = 1-float(min(distances))/float(length)
        print('Minimal distance: '+str(min_distance)+' of '+str(length))
        print('Minimal correlation percentage: '+str(min_correlation))
        
        try:
            minimals = scipy.genfromtxt(self.debug_file)
        except Exception, err:
            log.error('%s' % str(err))
            print('first time, so creating minimals')
            minimals = scipy.array([])
        
        minimals = scipy.hstack((minimals, scipy.array([min_correlation])))
        scipy.savetxt(self.debug_file, minimals)

        print('saved minimals to file')
        
        for fingerprint in possible_fingerprints:
            try:
                # trying to decommit
                self.private_key, corr = crypto_fuzzy_jw.JW_decommit(hash, delta, fingerprint, m=self.rs_code_m, n=self.rs_code_n, symsize=self.rs_code_symsize)
            except Exception, err:
                log.error('%s' % str(err))
                
            else:
                # if hash is the same accept key agreement,
                # test is in JW_decommit, try fails when not!
                # return True for accepted connection
                return True
        
        # if every fingerprint fails to decommit pairing fails
        return False
        
    def remote_get_data(self):
        """10. get data server object
        
        Bob answers with ``DataServer`` object.
        """
        log.info('10. get data server object ')
                
        # return DataServer object for transferring messages
        data_server = DataServer(self)
        return data_server
        
class DataServer(pb.Referenceable):
    def __init__(self, pairing_server):
        """Initialize DataServer object
        
        :param pairing_server: Reference to ``PairingServer`` object
        :type pairing_server: PairingServer
        """
        self.pairing_server = pairing_server
        
    def remote_send_message(self, message):
        """13. send plain message
        
        :param message: Received message
        :type message: str
        """
        log.info('13. send plain message')
        
        log.info('received plain message:\n'+repr(message))
        
    def remote_send_encrypted_message(self, ciphertext):
        """13. send encrypted plain message
        
        :param ciphertext: Received ciphertext
        :type ciphertext: str
        """
        log.info('13. send encrypted plain message')
        
        private_key = self.pairing_server.private_key

        # use key to generate key usefull fo aes
        aes_key = generate_key_for_aes(private_key)
        
        # doing decryption
        aes_obj = AES.new(aes_key, AES.MODE_ECB)
        message = aes_obj.decrypt(ciphertext)
        
        log.info('decrypted message:\n'+repr(message))


if __name__ == '__main__':
    """start main as default
    """
    main()
