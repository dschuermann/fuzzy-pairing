# -*- coding: utf-8 -*-
"""
Check Time from NTP Server

    :platform: Linux
    :synopsis: NTP Check

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""

from socket import socket, AF_INET, SOCK_DGRAM
import struct, time
import logging
# get logger
log = logging.getLogger("fuzzy_pairing")

# time server and the port
time_server = ('ptbtime1.ptb.de', 123)
 
# unix epoch
unix_epoch = 2208988800L

def time_in_sync():
    """check if local time is in sync with NTP server time
    
    checks against ``time_server`` defined in ``helper_check_ntp``.
    
    :return: If local and Server time are in sync it return True
    """
    # opens socket
    client = socket( AF_INET, SOCK_DGRAM )
    
    # data to send to server
    data = '\x1b' + 47 * '\0'
    
    try:
        # send the data to the server
        client.sendto(data, time_server)

        # receive data 
        data, address = client.recvfrom( 1024 )
    except Exception, err:
            log.error('%s' % str(err))
    else:
        # successfull received
        if data:
            log.debug('NTP server: '+str(time_server)+str(address))
            
            # process the data, this is where it being formatted. 
            time_now = struct.unpack( '!12I', data )[10]
            
        	# throws an exception if the time is 0
            if time_now == 0:
                raise 'NTP invalid response'
            
            time_ntp = time_now - unix_epoch
            time_local = int(time.time())
            
            # log infos
            log.debug('NTP Time: '+str(time_ntp))
            log.debug('Local Time: '+str(time_local))
            
            # 0, -1, +1 difference is ok!
            if (time_ntp==time_local) or (time_ntp-1==time_local) or (time_ntp+1==time_local):
                return True
            else:
                log.info('Please use this as your systems NTP server: '+str(time_server))
                return False
         
        else:
            raise 'NTP no data returned'
    
# Test
if __name__ == '__main__':
    """start main as default
    """
    print time_in_sync()