# -*- coding: utf-8 -*-
import time
import thread
import gobject
import pygst
pygst.require("0.10")
import gst

import os

from helper_audio import load_mono

import logging
# get logger
log = logging.getLogger("fuzzy_pairing")

class AudioRecording:
    """
    Simple audio recorder that records the input audio
    and saves it as an MP3 audio file.
    (for example audio input from a microphone)
    """
    def __init__(self, filename, duration):
        self.is_playing = False
        self.num_buffers = -1
        self.error_message = ""
        
        self.filename = filename
        self.duration = duration
        
        self.constructPipeline()
        self.connectSignals()

    def constructPipeline(self):
        # Create the pipeline instance
        self.recorder = gst.Pipeline()

        # Define pipeline elements
        # source
        self.audiosrc = gst.element_factory_make("autoaudiosrc")
        
        # audiofilter
        self.audiorate = gst.element_factory_make("audiorate")
        self.audioconvert = gst.element_factory_make('audioconvert')
        self.audioresample = gst.element_factory_make('audioresample')
        
        # set capsfilter
        outcaps = gst.Caps("audio/x-raw-int, endianness=byte_order, signed=(boolean)true, width=16, depth=16, rate=44100, channels=1")
        self.capsfilter = gst.element_factory_make("capsfilter") 
        self.capsfilter.props.caps = outcaps

        # encoder
        self.encoder = gst.element_factory_make("wavenc")
        
        # filesink
        self.filesink = gst.element_factory_make("filesink")
        self.filesink.set_property("location", self.filename)


        # Add elements to the pipeline
        self.recorder.add(self.audiosrc,
                        self.audiorate,
                        self.audioconvert,
                        self.audioresample,
                        self.capsfilter,
                        self.encoder,
                        self.filesink)

        # Link elements in the pipeline.
        gst.element_link_many(self.audiosrc,
                              self.audiorate,
                              self.audioconvert,
                              self.audioresample,
                              self.capsfilter,
                              self.encoder,
                              self.filesink)

    def connectSignals(self):
        """
        Connects signals with the methods.
        """
        # Capture the messages put on the bus.
        bus = self.recorder.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.message_handler)
        
        # init as paused
        self.recorder.set_state(gst.STATE_PAUSED)

    def record_start(self, end_time):
        """
        Record the audio until end_time
        """
        self.is_playing = True
        self.recorder.set_state(gst.STATE_PLAYING)
        log.debug("Recording GStreamer started at "+str(time.time()))
        # record until end_time
        while self.is_playing:
            if (time.time() >= end_time):
                # stop recording
                self.record_stop()
                
                break

    def record_stop(self):
        """
        Stop Recording
        """
        self.recorder.set_state(gst.STATE_NULL)
        self.is_playing = False
        log.debug("Recording stopped at "+str(time.time()))
        
        # error messages?
        if self.error_message:
            print self.error_message

    def message_handler(self, bus, message):
        """
        Capture the messages on the bus and
        set the appropriate flag.
        """
        msgType = message.type
        if msgType == gst.MESSAGE_ERROR:
            self.recorder.set_state(gst.STATE_NULL)
            self.is_playing = False
            self.error_message =  message.parse_error()
        elif msgType == gst.MESSAGE_EOS:
            self.recorder.set_state(gst.STATE_NULL)
            self.is_playing = False


def record_at_time(filename, duration, start_time):
    # init recorder
    recording = AudioRecording(filename, duration)
    
    end_time = start_time+duration
    
    log.debug("Recording Start time: "+str(start_time))
    log.debug("Recording End time: "+str(end_time))
    
    # starting at start_time
    while True:
        if (time.time() >= start_time):
            # now go on!
            break

    log.info('Recording thread started at '+str(time.time()))
    
    # record in thread
    thread.start_new_thread(recording.record_start, (end_time,))
    
    
    # init and start gobject c threads
    loop = gobject.MainLoop()
    gobject.threads_init()
    context = loop.get_context()
    
    # record and do thread loop until end_time
    while True:
        # do gobject iteration
        context.iteration(True)
        
        if (time.time() >= end_time):
            # terminate gobject thread
            loop.quit()
            
            break
    
    # load recorded file
    recording_data, recording_samplerate = load_mono(filename)
    
    return recording_data, recording_samplerate