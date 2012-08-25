# -*- coding: utf-8 -*-
"""
Fuzzy Pairing Client Implementation
    
    :platform: Linux
    :synopsis: Client Implementation

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""
import time
import logging
import scipy

import thread, os

import crypto_fuzzy_jw
import fingerprint_energy_diff

from Crypto.Cipher import AES

from twisted.spread import pb
from twisted.internet import reactor

from helper_audio_recording import record_at_time
from helper_audio import load_stereo, load_mono

from helper_check_ntp import time_in_sync
from helper_implementation import generate_key_for_aes

# Logging all above INFO level, output to stderr
logging.basicConfig(#format='%(asctime)s %(levelname)-8s %(message)s')
                    format='%(levelname)-8s %(message)s')
log = logging.getLogger("fuzzy_pairing")
log.setLevel(logging.DEBUG)
    
def main():
    # start client and connect to port 4200
    factory = pb.PBClientFactory()
    reactor.connectTCP("192.168.178.2", 4200, factory) # Insert appropriate IP here when using two machines
#    reactor.connectTCP("localhost", 4200, factory)

    # instatiate agreement object of client
    pairing = PairingClient(device_id="Alice")
    # get root object (Agreement) and start request_connection
    factory.getRootObject().addCallback(pairing.request_connection)
    
    # start client
    reactor.run()

class PairingClient:
    def __init__(self, device_id):
        """Initialize PairingClient object
    
        :param device_id: Identification string, should be "Alice"
        :type decide_id: str
        """
        self.pairing_server = None
        self.fingerprint = None
        self.delta = None
        self.hash = None
        self.private_key = None
        self.device_id = device_id
        self.recording_data = None
        self.recording_samplerate = None
        self.recording_use_file = False
        self.recording_file = 'client_recording.wav'
        self.rs_code_m = 152
        self.rs_code_n = 512
        self.rs_code_symsize = 10
        self.check_ntp = False
        self.debug = False # Using this means NO security!
    
    def request_connection(self, pairing_server):
        """1. Alice requests connection
    
        :param pairing_server: PairingServer object from Bob
        """
        log.info('1. Alice requests connection')
        
        # set agreement reference to server on self object
        self.pairing_server = pairing_server
        
        # remote call for requesting connection
        # very very simple implementation with device_id
        accept_connection = self.pairing_server.callRemote("connection", self.device_id)
        
        # get answer
        accept_connection.addCallbacks(self.answer_connection)
        
    def answer_connection(self, accept_connection):
        """3. Alice gets answer from Bob
        
        Alice checks if connection was acepted, then checks NTP time
        and starts synchronized recording
        
        :param accept_connection: callback from Bob
        :type accept_connection: bool
        """
        log.info('3. Alice gets answer from Bob')
        
        if accept_connection:
            log.info('Bob accepted connection')
            if self.check_ntp:
                # check NTP
                if not time_in_sync():
                    log.info('Local time not in sync with NTP')
                    self.stop_pairing()
                else:
                    log.info('NTP time ok')
            
            # here 4 and 5 are called synchron!
            # record own data in thread
            
            # define start time
            start_time = time.time()+3
            
            # for testing with sound
            #thread.start_new_thread(os.system, ("sleep 2; aplay test_background.wav",))
            
            
            # call local on client
            reactor.callInThread(self.do_recording, start_time)
            # call remote on server
            successfull_server_recording = self.pairing_server.callRemote("recording", start_time)
            successfull_server_recording.addCallbacks(self.answer_recording)
        else:
            log.info('Bob denied connection')
            self.stop_pairing()
        
    def do_recording(self, start_time):
        """4. Alice requests recording
        (4 and 5 are called synchronous at ``start_time``)
        
        Function waits until ``start_time`` and then starts recording
        
        :param start_time: Absolute time when recording should start
        :type start_time: int
        """
        log.info('4. Alice requests recording')
        
        if self.recording_use_file:
            # load recording from file
            #left_channel, right_channel, self.recording_samplerate = load_stereo(self.recording_file)
            #self.recording_data = left_channel
            self.recording_data, self.recording_samplerate = load_mono(self.recording_file)
        else:
            # start recording at start_time
            self.recording_data, self.recording_samplerate = record_at_time("client.wav", 7, start_time)
        
    def answer_recording(self, successfull_server_recording):
        """6. Alice gets answer of recording
        
        If Alice gets successfull answer from Bob, Alice starts
        the agreement
        
        :param successfull_server_recording: callback from Bob
        :type successfull_server_recording: bool
        """
        log.info('6. Alice gets answer of recording')
        
        # wait a little bit to ensure that the own recording has ended
        time.sleep(1)
        
        if successfull_server_recording:
            log.info('Bob recorded successfully')
            
            # start agreement
            self.request_agreement()
        else:
            log.info('Bobs recording failed')
            self.stop_pairing()
        
    
    def request_agreement(self):
        """7. Alice starts key agreement
        generate fingerprint and doing fuzzy commitment
        send hash and delta to Bob
        """
        log.info('7. Alice starts key agreement')

        #===============================================================================
        # Fingerprinting and Fuzzy Cryptography
        #===============================================================================
        # generate fingerprint
        self.fingerprint = fingerprint_energy_diff.get_fingerprint(self.recording_data, self.recording_samplerate)
        
        # save fingerprint for debugging
        scipy.savetxt("client_fingerprint.txt", self.fingerprint)

        log.debug('Alice fingerprint:\n'+str(self.fingerprint))
        
        # doing commit, rs codes can correct up to (n-m)/2 errors
        self.hash, self.delta, self.private_key = crypto_fuzzy_jw.JW_commit(self.fingerprint, m=self.rs_code_m, n=self.rs_code_n, symsize=self.rs_code_symsize)
        
        log.debug('Alice Blob:\nHash:\n'+str(self.hash)+'\nDelta:\n'+str(self.delta))
        
        # save delta for debugging
        scipy.savetxt("client_delta.txt", self.delta)
        
        # remote call for key agreement
        # using debug means sending also the fingerprint in clear text!!!
        # meaning no security!
        if self.debug:
            accept_agreement = self.pairing_server.callRemote("agreement_debug", self.fingerprint.tolist(), self.hash, self.delta.tolist())
            accept_agreement.addCallbacks(self.answer_agreement)
        else:
            accept_agreement = self.pairing_server.callRemote("agreement", self.hash, self.delta.tolist())
            accept_agreement.addCallbacks(self.answer_agreement)
        
    def answer_agreement(self, accept_agreement):
        """9. Alice gets answer of agreement from Bob
        
        If Bob accepted agreement Alice tries to get ``DataServer`` object from Bob
        
        
        :param accept_agreement: Callback from Bob
        :type accept_agreement: bool
        """
        log.info('9. Alice gets answer of agreement from Bob')
        
        if accept_agreement:
            log.info('Bob accepted agreement')
            
            # get DataServer object
            data_server = self.pairing_server.callRemote("get_data")
            data_server.addCallbacks(self.got_data)
        else:
            log.info('Bob denied agreement')
            self.stop_pairing()
            
    def got_data(self, data_server):
        """11. Alice got the data server object for transmitting messages
        
        Called if Alice got ``DataServer`` object from Bob.
        Now Alice creates ``DataClient`` object and starts sending a
        message
        
        :param data_server: Callback object from Bob
        :type data_server: DataServer
        """
        log.info('8. Alice got the data server object for transmitting messages')
        
        # new DataClient object
        data_client = DataClient(self, data_server)

        # send message
        time.sleep(1)
        data_client.send_encrypted_message("Hello, this is a message")
        
    def stop_pairing(self):
        log.error("Pairing failed")
        reactor.stop()
        
class DataClient:
    def __init__(self, pairing_client, data_server):
        """Initialize DataClient object
        
        :param pairing_client: Reference to ``DataClient`` object
        :type pairing_client: DataClient
        :param data_server: Reference to ``DataServer`` object
        :type data_server: DataServer
        """
        self.pairing_client = pairing_client
        self.data_server = data_server
        
    def send_message(self, message):
        """12. Alice sends message to Bob
        
        Remote call to send ``message`` **unencrypted** to Bob
        
        :param message: Message to send
        :type message: str
        """
        log.info('12. Alice sends message to Bob')
        
        self.data_server.callRemote("send_message", message)
        
    def send_encrypted_message(self, message):
        """12. Alice sends encrypted message to Bob
        
        Remote call to send ``message`` **encrypted** to Bob.
        With ``generate_key_for_aes`` it generates an AES key
        from the ``private_key`` attribute of the ``DataClient`` object.
        This AES key is used to encrypt with AES.
        
        :param message: Message to send
        :type message: str
        """
        log.info('12. Alice sends encrypted message to Bob')
        
        private_key = self.pairing_client.private_key
        
        # use key to generate key usefull fo AES
        aes_key = generate_key_for_aes(private_key)
        
        # padding message to a length of a multiple of 16
        while ((len(message) % 16) != 0):
            message += 'X'
        
        # do encryption with AES
        aes_obj = AES.new(aes_key, AES.MODE_ECB)
        ciphertext = aes_obj.encrypt(message)
        
        log.info('Alice ciphertext:\n'+repr(ciphertext))
        
        # little fix to delay the remote call
        time.sleep(1)
        self.data_server.callRemote("send_encrypted_message", ciphertext)


if __name__ == '__main__':
    """start main as default
    """
    main()
