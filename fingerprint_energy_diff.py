# -*- coding: utf-8 -*-
"""
Fingerprinting based on Energy Differences
"A Highly robust Audio Fingerprinting System" by Haitsma & Kalker

    :platform: Linux
    :synopsis: Fingerprinting based on Energy Differences

.. moduleauthor:: Dominik Schuermann <d.schuermann@tu-braunschweig.de>

"""
import scipy
from scipy import fftpack
from scipy import signal
import logging
import sys
# get logger
log = logging.getLogger("fuzzy_pairing")

def get_frames(data, samplerate, overlap_factor=0.0):
    """Split data into frames
    
    :param data: One-dimensional scipy.array with the audio data
    :type data: scipy.array
    :param samplerate: samplerate of data
    :type samplerate: int
    :return: frames
    """
    log.debug('Fingerprinting: get_frames')
    data_length = len(data)
    
    log.debug('data: '+repr(data))
    log.debug('data length: '+str(data_length))
    
    # calculate length of one frame
    # one frame should be 0.37 seconds, specified in paper
    frame_length = int(0.37 * samplerate)
    
    log.debug("overlap factor: "+str(overlap_factor))
    overlap = frame_length * overlap_factor
    log.debug("overlap: "+str(overlap))
    
    frames_count = int((data_length-overlap) / frame_length)
    
    log.debug('length of one frame: '+repr(frame_length))
    log.debug('number of frames: '+repr(frames_count))
    
    
    # split into number of frames_count frames
    frames = range(frames_count)
    for i in frames:
        frame_start = frame_length * i
        frame_end = frame_length * (i+1) + overlap # + overlap!!!
        frames[i] = scipy.array(data[frame_start:frame_end])

    return frames
    
    
def frames_fft(frames, weighted = True):
    """doing fast fourier transformations on each frame vector
    in frames
    
    Optional TODO: Implement filter
    
    :param frames: input scipy.array of audio frames
    :type frames: scipy.array
    :param weighted: Should it be weighted by hamming-window?
    :type weighted: bool
    :return: frames_frequency -- Frequencies per frame 
    """
    log.debug('Fingerprinting: frames_fft')
    
    frames_count = len(frames)

    # TODO: Filter?
    # filter initalising
    # length of first frame
    #n = len(frames[0])
    ## Lowpass filter
    #a = scipy.signal.firwin(n, cutoff = 0.2, window = 'hanning')
    ## Highpass filter with spectral inversion
    #b = - scipy.signal.firwin(n, cutoff = 0.8, window = 'hanning'); b[n/2] = b[n/2] + 1
    ## Combine into a bandpass filter
    #d = - (a+b); d[n/2] = d[n/2] + 1 
    
    # Hanning Window with length of first frame,
    # so you can use it on every frame
    window = signal.get_window('hanning', len(frames[0]))
    
    # allocating memory for frames_frequency array
    frames_frequency = range(frames_count)
    for i in frames_frequency:
        # weighted by a hanning window
        # multiplication with window elementwise
        if weighted:
            frames_frequency[i] = frames[i]*window
        else:
            frames_frequency[i] = frames[i]
        
        
        # TODO: use filter
        #frames_frequency[i] = signal.lfilter(d, 1, frames[i])
        
        # do fft and use absolute value
        frames_frequency[i] = scipy.array(abs(fftpack.fft(frames_frequency[i])))
        
        # cut out mirrored
        frames_frequency[i] = frames_frequency[i][0:len(frames_frequency[i])/2]
    
    return frames_frequency
    
    
def calculate_energy(frames_frequency, frequency_band_length):
    """divide into frequency bands and calculate energy
    
    Optional TODO: Implement band range (bottom and top)
    
    
    :param frames_frequency: scipy.array with the frames in frequency domain
    :type frames_frequency: scipy.array
    :param frequency_band_length: length of every frequency band
    :type frequency_band_length: int
    :return: frames_energy -- Two-dimensional array with energy list per Frame
    """
    log.debug('Fingerprinting: calculate_energy')
    
    frames_count = len(frames_frequency)

    # fill later with energies per frame
    frames_energy = range(frames_count)
    
    # length of one frame
    frame_length = len(frames_frequency[0])
    
    # define frequency bands
    frequency_bands = range(0, frame_length, frequency_band_length)
    #log.debug('number of frequency bands: '+repr(len(frequency_bands)))
    
    # every frame
    for i, frame in enumerate(frames_frequency):
        # energy of this frame, calculated below
        energy = scipy.array([])
        
        #log.debug('calcuating band energy of frame '+str(frame))
        # calculate energy on every frequency band and append energy
        # to vector frame_energy
        for frequency in frequency_bands:
            
            # calculate band_energy over every frequency in the frequency_band
            band_energy = 0
            for j in range(frequency, frequency+frequency_band_length, 1):
                # only when we are in the available frequency band
                if (j < frame_length):
                    band_energy += frame[j]
                    
            # append this energy squared to the frame_vector
            energy = scipy.append(energy, band_energy**2)
            
        # fill energy list with scipy.arrays for every frame with energys from the bands
        frames_energy[i] = energy
    
    #log.debug('frames_energy list with scipy.arrays: '+repr(frames_energy))
    return frames_energy
    
    
def calculate_difference(frames_energy):
    """calculate difference of energies
    
    Implementation following paper "A Highly Robust Audio Fingerprinting System"
    
    :math:`F(n,m)=1` if :math:`E(n,m)-E(n,m+1)-(E(n-1,m)-E(n-1,m+1))>0`
    
    :math:`F(n,m)=0` if :math:`E(n,m)-E(n,m+1)-(E(n-1,m)-E(n-1,m+1))\leq 0`
    
    :param frames_energy: frames of energys
    :type frames_energy: scipy.array
    :return: fingerint
    """
    log.debug('Fingerprinting: calculate_difference')

    # fingerprint vector
    fingerprint = scipy.array([], dtype=int)
    
    # first frame is defined as previous frame
    prev_frame = frames_energy[0]
    print str(len(frames_energy))
    del frames_energy[0]
    
    for n, frame in enumerate(frames_energy):
        # every energy of frequency bands until length-1
        for m in range(len(frame)-1):
            # calculate difference with formula from paper            
            if (frame[m]-frame[m+1]-(prev_frame[m]-prev_frame[m+1]) > 0):
                fingerprint = scipy.append(fingerprint, 1)
            else:
                fingerprint = scipy.append(fingerprint, 0)
            
        prev_frame = frame
        
    return fingerprint



def calculate_fingerprint(data, samplerate):
    """calculate fingerprint of given data
    
    :param data: Should be a one dimensional vector, that holds the audiodata in mono
    :type data: list
    :param samplerate: Samplerate of audio data
    :type samplerate: int
    :return: fingerprint
    """
    # break data into frames
    frames = get_frames(data, samplerate, overlap_factor=0.0)
    # Overlapping makes no improvments:
    #frames = get_frames(data, samplerate, overlap_factor=31.0/32.0)
    
    # do fft on each frame
    frames_frequency = frames_fft(frames, weighted = True)
    
    # divide into frequency bands and calculate energy
    frames_energy = calculate_energy(frames_frequency, 250)

    # calculate energy difference
    fingerprint = calculate_difference(frames_energy)
    
    # return fingerprint
    return fingerprint
    
def get_fingerprint(data, samplerate):
    """Just a wrapper of ``calculate_fingerprint`` to get
    the first 512 bits only.
    
    :param data: Should be a one dimensional vector, that holds the audiodata in mono
    :type data: list
    :param samplerate: Samplerate of audio data
    :type samplerate: int
    :return: fingerprint -- 512 bit fingerprint
    """
    # calculate fingerprint
    fingerprint = calculate_fingerprint(data, samplerate)
    
    # take only first 512 bits
    # -> (2 fingerprintblocks with total 16 frames)
    fingerprint = fingerprint[0:512]
    
    return fingerprint
