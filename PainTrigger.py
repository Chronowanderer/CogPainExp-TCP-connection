from PyDAQmx import *
from ctypes import *
import numpy as np
import time
import socket
import os


DEVICE = [b'Dev1']
CHANNEL_INPUT = [b'ai0']
CHANNEL_OUTPUT = [b'ao0', b'ao1']

Temporal_Gap = 0.5 # Basic temporal gap between colliding and shocking (sec)
Tolerance_Gap = 1 # Maximum temporal gap between colliding and shocking (sec)
Threshold_TR = 3.0 # Threshold for vaild TR pulse

FILE_PainRecord = 'ExpData/PainSignalRecord.csv'
FILE_TRRecord = 'ExpData/TRSignalRecord.csv'


class ElectricShock(Task):
    def __init__(self, inName, outName, bodyPart, shockDuration, startTime, is_MRI, filename_TR, clientsocket):
        Task.__init__(self)
        self.start = startTime
        self.is_MRI = is_MRI
        self.filename_TR = filename_TR
        self.clientsocket = clientsocket

        # Stimulation Setting Code
        self.shockIntensity = 5
        self.stim = [0] * 1 + [self.shockIntensity] * 2 + [0] * 1  # Stimulus with 2ms width
        self.stim = self.stim * 10  # x10 in 40ms, 250Hz
        self.stim = np.array(self.stim, dtype = np.float64)
        self.zerostim = np.zeros(len(self.stim))

        self.samplerate = 1000
        self.samplelen = 10
        self.data = np.zeros((self.samplelen,), dtype=np.float64)

        # Shock Input Setting
        self.bodyPart = bodyPart
        self.shockDuration = shockDuration
        self.inName = inName
        self.outName = outName

        # Shock Task Setting
        if self.inName is not None:
            self.CreateAIVoltageChan(self.inName, '', DAQmx_Val_RSE, -10.0, 10.0, DAQmx_Val_Volts, None)
            self.CfgSampClkTiming('', self.samplerate, DAQmx_Val_Rising, DAQmx_Val_ContSamps, self.samplelen)
            self.sampsRead = int32()
            self.AutoRegisterEveryNSamplesEvent(DAQmx_Val_Acquired_Into_Buffer, self.samplelen, 0)
            self.AutoRegisterDoneEvent(0)
        if self.outName is not None:
            self.CreateAOVoltageChan(self.outName, '', -10.0, 10.0, DAQmx_Val_Volts, None)
            self.sampsWritten = int32()

    def EveryNCallback(self):
        self.ReadAnalogF64(self.samplelen, 10.0, DAQmx_Val_GroupByScanNumber,
                           self.data, self.samplelen, byref(self.sampsRead), None)

        if not self.is_MRI:
            output = b'2'  # Non MRI mode
        elif self.ReadTR(self.filename_TR):
            output = b'1'  # MRI mode with TR pulse received
        else:
            output = b'0'  # MRI mode with TR pulse not received
        try:
            self.clientsocket.send(output)
            # print(time.time(), ': Message ', output, ' sent.')
            pass
        except IOError as e:
            print(e.strerror)

        return 0  # The function should return an integer

    def ReadTR(self, filename_TR):
        # Obtain TR signal from MRI
        filename_TR.write(str(time.time()) + ',' + str(self.data[0]))
        filename_TR.write('\n')
        filename_TR.flush()
        os.fsync(filename_TR.fileno())

        self.isTR = (self.data[0] > Threshold_TR)
        return self.isTR

    def Shock(self, temporal_gap = Temporal_Gap):
        # Task Configure Code
        if self.shockDuration > 0:
            time.sleep(temporal_gap)
            self.WriteAnalogF64(len(self.stim), True, 10.0, DAQmx_Val_GroupByChannel,
                                self.stim, byref(self.sampsWritten), None)
            print("DAQhardware.writeValue(): chanNames = %s val = %s" % (repr(self.outName), repr(self.stim)))
        else:
            self.WriteAnalogF64(len(self.stim), True, 10.0, DAQmx_Val_GroupByChannel,
                                self.zerostim, byref(self.sampsWritten), None)
            print("DAQhardware.writeValue(): chanNames = %s val = %s" % (repr(self.outName), repr(self.zerostim)))

        # Print for debug
        print("DAQhardware.setupAnalogOutput(): Wrote %d samples" % self.sampsWritten.value)
        print("Task duration: %.3f sec" % (time.time() - self.start))


class SocketConnection:
    def __init__(self, host, port):
        self.address = (host, port)

    def connect(self, is_MRI = False):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(self.address)
        server.listen(5)
        try:
            connectionFlag = False

            filename_TR = open(FILE_TRRecord, mode='a+')
            filename_TR.write('timestamp,TR')
            filename_TR.write('\n')
            filename_TR.flush()

            filename_pain = open(FILE_PainRecord, mode='a+')
            filename_pain.write('timestamp,bodyPart,mode')
            filename_pain.write('\n')
            filename_pain.flush()

            if not connectionFlag:
                clientsocket, _ = server.accept()
                # print('accept')
                for devName in DEVICE:
                    inName = devName + b'/' + CHANNEL_INPUT[0]
                    task_input = ElectricShock(inName, None, None, None, time.time(), is_MRI, filename_TR, clientsocket)
                    task_input.StartTask()
                    # print('Task started')

            while True:
                connectionFlag = self.read_from_client(clientsocket, filename_pain, is_MRI)

            task_input.StopTask()
            task_input.ClearTask()

            if not connectionFlag:
                clientsocket.close()
            filename_TR.close()
            filename_pain.close()

        except IOError as e:
            print(e.strerror)

    def read_from_client(self, clientsocket, filename_pain, is_MRI):
        content = None
        try:
            input = clientsocket.recv(4096)
            if input:
                content = input.decode('ascii')
        except IOError as e:
            print(e.strerror)

        if content:
            data = content.strip().split(' ')
            bodyPart, shockDuration = 0, 0
            for i, j in enumerate(data):
                if int(j) >= 10: # ENSURE at most 10 body parts and shock duration above 10 ms!!!
                    bodyPart, shockDuration = int(data[i - 1]), int(j)
                    break
            if shockDuration > 1:
                print('Input: ', bodyPart, ' ', shockDuration)

                filename_pain.write(str(time.time()) + ',' + str(bodyPart) + ',R')
                filename_pain.write('\n')
                filename_pain.flush()
                os.fsync(filename_pain.fileno())

                # DAQmx Configure Code
                for devName in DEVICE:
                    outName = devName + b'/' + CHANNEL_OUTPUT[bodyPart]
                    task_output = ElectricShock(None, outName, bodyPart, shockDuration, time.time(), is_MRI, None, clientsocket)
                    task_output.StartTask()

                    task_output.Shock()

                    filename_pain.write(str(time.time()) + ',' + str(bodyPart) + ',W')
                    filename_pain.write('\n')
                    filename_pain.flush()
                    os.fsync(filename_pain.fileno())

                    task_output.StopTask()
                    task_output.ClearTask()

            return True
        else:
            return False


def Test(bodyPart, shockDuration, is_MRI):
    outName = DEVICE[0] + b'/' + CHANNEL_OUTPUT[bodyPart]
    task_output = ElectricShock(None, outName, bodyPart, shockDuration, time.time(), is_MRI, None, None)
    task_output.StartTask()
    task_output.Shock()
    task_output.StopTask()
    task_output.ClearTask()
