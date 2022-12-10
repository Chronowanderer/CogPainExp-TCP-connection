# CogPainExp-TCP-connection
 TCP connection codes for Cognitive Pain Experiments.

## Introduction
Two different stimulators (DS5) are connected to an external I/O Device (NI USB-6212) through different ports, which is then connected to the Python server. The I/O Device is also connected with a 1-0 task trigger (e.g. for TR pulse from the scanner), of which the signal comes to the server and then is sent to the Unity client to launch the task at an appropriate time. On the other hand, the Unity client is attached to a persistent non-visible GameObject in the Unity task. When the player has done something for a stimulation, the corresponding stimulation information message is directly sent from the Unity client to the Python server, which then generates a real stimulation from those stimulators with the help of the I/O device. Both the 1-0 trigger data and stimulation data are recorded and saved based on the server system time, so that to enable the temporal alignment between task stimulation and trigger timing.

## Application
[Desktop-based VR pain learning task](https://github.com/Chronowanderer/CogPainExp-Desktop-App)

Immersive VR pain learning task (will be published soon)

## Related tutorial
[Virtual reality experiment setup](https://github.com/ShuangyiTong/VRPainExptGuide)
