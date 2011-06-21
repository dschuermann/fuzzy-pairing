Documentation of Fuzzy Pairing
******************************

This Python program is part of my bachelor thesis "Nutzung von Kontextinformationen zur Herstellung eines sicheren Kommunikationskanals".

Abstract of the corresponding bachelor thesis
=============================================

This bachelor thesis deals with the secure communication between wireless devices using context information. It investigates the benefits of context information to establish an encrypted communication and provides an example implementation. By making use of time-varying input signals to generate a secret key between the two devices, it is possible to create an ad-hoc secure channel between the devices with the same context. Because of this, the manual distribution of secret keys between the devices will be obsolet.

An audio fingerprinting procedure generates a bit sequence from audio inputs of two physically neighbouring devices. As a result of the proximity of both devices, the audio sequences and thus the generated bit sequences are similar. These results are used as the basis for establishing a secure communication. Special methods from the field of fuzzy cryptography are used to generate a secure communication channel, in spite of the difference between the bit sequences.

Contents
========

.. toctree::
   :maxdepth: 2

   fuzzy
   fingerprint
   implementation
   helper
   other


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

