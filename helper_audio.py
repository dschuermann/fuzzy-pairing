# -*- coding: utf-8 -*-
"""
Functions to open audio files and to record from default microphone

    :platform: Linux
    :synopsis: Audio Helper

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""
import logging
# get logger
log = logging.getLogger("fuzzy_pairing")


from scipy.io import wavfile

from helper_audio_decoder import read_as_array

def load_stereo(filename):
    """load stereo audio file with gstreamer
    
    :param filename: name of file, relative path
    :type filename: str
    :return: left_channel -- Left channel as list
    :return: right_channel -- Right channel as list
    :return: samplerate -- Samplerate of audio file
    """
    data, duration, channels, samplerate = read_as_array(filename)
    log.debug("Load File "+filename+"\nduration: "+str(duration)+" seconds\nchannels: "+str(channels)+"\nsamplerate: "+str(samplerate))
    
    # seperate left and right channel
    left_channel = data[0,:]
    right_channel = data[1,:]
        
    return left_channel, right_channel, samplerate
    
def load_mono(filename):
    """load mono audio file with gstreamer
    
    :param filename: name of file, relative path
    :type filename: str
    :return: data -- Channel as list
    :return: samplerate -- Samplerate of audio file
    """
    data, duration, channels, samplerate = read_as_array(filename)
    log.debug("Load File "+filename+"\nduration: "+str(duration)+" seconds\nchannels: "+str(channels)+"\nsamplerate: "+str(samplerate))
    
    return data, samplerate

def load_wave_with_scipy(wavFile):
    """load Wave File with build in function from Scipy
    
    Can only open **.wav** files
    
    .. warning:: It has problems with many codecs
    
    :param filename: name of file, relative path
    :type filename: str
    :return: left_channel -- Left channel as list
    :return: right_channel -- Right channel as list
    :return: samplerate -- Samplerate of audio file
    """
    # open stereo wavefile
    samplerate, data = wavfile.read(wavFile)

    # seperate left and right channel
    left_channel = data[:,0]
    right_channel = data[:,1]
    
    return left_channel, right_channel, samplerate