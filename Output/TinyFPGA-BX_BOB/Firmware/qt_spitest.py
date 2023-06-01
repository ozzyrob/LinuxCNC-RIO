
import time
from struct import *
import sys
from PyQt5.QtWidgets import QWidget,QPushButton,QApplication,QListWidget,QGridLayout,QLabel,QSlider,QCheckBox
from PyQt5.QtCore import QTimer,QDateTime, Qt

SERIAL = ''
NET_IP = ''
if len(sys.argv) > 1 and sys.argv[1].startswith('/dev/tty'):
    import serial
    SERIAL = '/dev/ttyUSB0'
    ser = serial.Serial(SERIAL, 2000000, timeout=1)
elif len(sys.argv) > 1 and sys.argv[1] != '':
    NET_IP = sys.argv[1]
    NET_PORT = 2390
    print('IP:', NET_IP)
    import socket
else:
    import spidev
    bus = 0
    device = 1
    spi = spidev.SpiDev()
    spi.open(bus, device)
    spi.max_speed_hz = 4000000
    spi.mode = 0
    spi.lsbfirst = False

INTERVAL = 100

data = [0] * 30
data[0] = 0x74
data[1] = 0x69
data[2] = 0x72
data[3] = 0x77

JOINTS = 5
VOUTS = 1
VINS = 1
DOUTS = 3
DINS = 3

joints = [
    0,
    0,
    0,
    0,
    0,
]

jointcalcs = {0: ('oscdiv', 10000), 1: ('oscdiv', 10000), 2: ('oscdiv', 10000), 3: ('oscdiv', 10000), 4: ('oscdiv', 10000)}

vouts = [
    0,
]

douts = [
    0,
    0,
    0,
]

PRU_OSC = 48000000

vinminmax = [
    (-100, 100, 'frequency', 0),
]

vout_types = [
    'pwm',
]

vin_types = [
    'frequency',
]

voutminmax = [
    (0, 100, 'pwm', 10000),
]

JOINT_ENABLE_BYTES = 1
DIGITAL_OUTPUT_BYTES = 1
DIGITAL_INPUT_BYTES = 1



class WinForm(QWidget):
    def __init__(self,parent=None):
        super(WinForm, self).__init__(parent)
        self.setWindowTitle('SPI-Test')
        self.listFile=QListWidget()
        layout=QGridLayout()
        self.widgets = {}
        self.animation = 0
        self.doutcounter = 0
        self.error_counter_spi = 0
        self.error_counter_net = 0

        COLS = max(JOINTS, DOUTS, VOUTS, DINS, VINS)

        gpy = 0
        for jn in range(COLS):
            label = QLabel(f'       {jn}     ')
            layout.addWidget(label, gpy, jn + 3)
        gpy += 1

        layout.addWidget(QLabel(f'JOINTS:'), gpy, 0)
        layout.addWidget(QLabel(f'OUT'), gpy, 1)
        for jn in range(JOINTS):
            key = f'jcs{jn}'
            self.widgets[key] = QSlider(Qt.Horizontal)
            self.widgets[key].setMinimum(-jointcalcs[jn][1])
            self.widgets[key].setMaximum(jointcalcs[jn][1])
            self.widgets[key].setValue(0)
            layout.addWidget(self.widgets[key], gpy, jn + 3)
        gpy += 1
        for jn in range(JOINTS):
            key = f'jcraw{jn}'
            self.widgets[key] = QLabel(f'cmd: {jn}')
            layout.addWidget(self.widgets[key], gpy, jn + 3)
        gpy += 1
        for jn in range(JOINTS):
            key = f'jc{jn}'
            self.widgets[key] = QLabel(f'cmd: {jn}')
            layout.addWidget(self.widgets[key], gpy, jn + 3)
        gpy += 1

        layout.addWidget(QLabel(f'VARIABLE:'), gpy, 0)
        layout.addWidget(QLabel(f'OUT'), gpy, 1)
        for vn in range(VOUTS):
            layout.addWidget(QLabel(vout_types[vn]), gpy, vn + 3)
        gpy += 1


        #layout.addWidget(QLabel(f'VARIABLE:'), gpy, 0)
        layout.addWidget(QLabel(f'OUT'), gpy, 1)
        for vn in range(VOUTS):
            key = f'vos{vn}'
            self.widgets[key] = QSlider(Qt.Horizontal)
            self.widgets[key].setMinimum(voutminmax[vn][0])
            self.widgets[key].setMaximum(voutminmax[vn][1])
            self.widgets[key].setValue(0)
            layout.addWidget(self.widgets[key], gpy, vn + 3)
        gpy += 1


        for vn in range(VOUTS):
            key = f'vo{vn}'
            self.widgets[key] = QLabel(f'vo: {vn}')
            layout.addWidget(self.widgets[key], gpy, vn + 3)
        gpy += 1

        layout.addWidget(QLabel(f'DIGITAL:'), gpy, 0)
        layout.addWidget(QLabel(f'OUT'), gpy, 1)
        self.widgets["dout_auto"] = QCheckBox()
        layout.addWidget(self.widgets["dout_auto"], gpy, 2)
        for dbyte in range(DIGITAL_INPUT_BYTES):
            for dn in range(8):
                key = f'doc{dbyte}{dn}'
                self.widgets[key] = QCheckBox()
                self.widgets[key].setChecked(False)
                layout.addWidget(self.widgets[key], gpy, dbyte * 8 + dn + 3)
                if dbyte * 8 + dn == DOUTS - 1:
                    break
        gpy += 1

        layout.addWidget(QLabel(f'JOINTS:'), gpy, 0)
        layout.addWidget(QLabel(f'IN'), gpy, 1)
        for jn in range(JOINTS):
            key = f'jf{jn}'
            self.widgets[key] = QLabel(f'joint: {jn}')
            layout.addWidget(self.widgets[key], gpy, jn + 3)
        gpy += 1

        layout.addWidget(QLabel(f'VARIABLE:'), gpy, 0)
        layout.addWidget(QLabel(f'IN'), gpy, 1)
        for vn in range(VINS):
            layout.addWidget(QLabel(vin_types[vn]), gpy, vn + 3)
        gpy += 1

        #layout.addWidget(QLabel(f'VARIABLE:'), gpy, 0)
        layout.addWidget(QLabel(f'IN'), gpy, 1)
        for vn in range(VINS):
            key = f'vi{vn}'
            self.widgets[key] = QLabel(f'vin: {vn}')
            layout.addWidget(self.widgets[key], gpy, vn + 3)
        gpy += 1

        layout.addWidget(QLabel(f'DIGITAL:'), gpy, 0)
        layout.addWidget(QLabel(f'IN'), gpy, 1)
        for dbyte in range(DIGITAL_INPUT_BYTES):
            for dn in range(8):
                key = f'dic{dbyte}{dn}'
                self.widgets[key] = QLabel("0")
                layout.addWidget(self.widgets[key], gpy, dbyte * 8 + dn + 3)
                if dbyte * 8 + dn == DINS - 1:
                    break
        gpy += 1

        layout.addWidget(QLabel(''), gpy, 0)
        gpy += 1

        layout.addWidget(QLabel(f'ERRORS:'), gpy, 0)
        layout.addWidget(QLabel(f'SPI:'), gpy, 1)
        self.widgets["errors_spi"] = QLabel("0")
        layout.addWidget(self.widgets["errors_spi"], gpy, 2)

        layout.addWidget(QLabel(f'NET:'), gpy, 3)
        self.widgets["errors_net"] = QLabel("0")
        layout.addWidget(self.widgets["errors_net"], gpy, 4)
        gpy += 1

        self.setLayout(layout)

        self.timer=QTimer()
        self.timer.timeout.connect(self.runTimer)
        self.timer.start(INTERVAL)

    def runTimer(self):

        #data = [0] * {project['data_size'] // 8}
        data[0] = 0x74
        data[1] = 0x69
        data[2] = 0x72
        data[3] = 0x77

        try:

            for jn in range(JOINTS):
                key = f"jcs{jn}"
                joints[jn] = int(self.widgets[key].value())

                key = f"jcraw{jn}"
                self.widgets[key].setText(str(joints[jn]))

            for vn in range(VOUTS):
                key = f"vos{vn}"
                vouts[vn] = int(self.widgets[key].value())
                key = f"vo{vn}"
                self.widgets[key].setText(str(vouts[vn]))

            if self.widgets["dout_auto"].isChecked():
                for dbyte in range(DIGITAL_OUTPUT_BYTES):
                    for dn in range(8):
                        key = f"doc{dbyte}{dn}"
                        stat = (self.animation - 1) == dbyte * 8 + dn
                        self.widgets[key].setChecked(stat)
                        if dbyte * 8 + dn == DOUTS - 1:
                            break

                if self.doutcounter > 10:
                    self.doutcounter = 0
                    if self.animation >= DOUTS:
                        self.animation = 0
                    else:
                        self.animation += 1
                else:
                    self.doutcounter += 1

            douts = []
            for dbyte in range(DIGITAL_OUTPUT_BYTES):
                douts.append(0)
                for dn in range(8):
                    key = f"doc{dbyte}{dn}"
                    if self.widgets[key].isChecked():
                        douts[dbyte] |= (1<<(dn))
                    if dbyte * 8 + dn == DOUTS - 1:
                        break


            bn = 4
            for jn, value in enumerate(joints):
                # precalc
                if value == 0:
                    value = 0
                elif jointcalcs[jn][0] == "oscdiv":
                    value = int(PRU_OSC / value)

                key = f"jc{jn}"
                self.widgets[key].setText(str(value))

                joint = list(pack('<i', value))
                for byte in range(4):
                    data[bn + byte] = joint[byte]
                bn += 4

            for vn, value in enumerate(vouts):
                if voutminmax[vn][2] == 'sine':
                    if value != 0:
                        value = int(PRU_OSC / value / voutminmax[vn][3])
                    else:
                        value = 0
                elif voutminmax[vn][2] == 'pwm':
                    value = int(value * (PRU_OSC / voutminmax[vn][3]) / 100)
                elif voutminmax[vn][2] == 'rcservo':
                    value = int(((value + 300)) * (PRU_OSC / 200000))
                elif voutminmax[vn][2] == 'udpoti':
                    value = value
                elif voutminmax[vn][2] == 'spipoti':
                    value = value
                elif voutminmax[vn][2] == 'frequency':
                    if value != 0:
                        value = int(PRU_OSC / value)
                    else:
                        value = 0

                print(vn, value)

                vout = list(pack('<i', (value)))
                for byte in range(4):
                    data[bn + byte] = vout[byte]
                bn += 4


            # jointEnable and dout (TODO: split in bits)
            for dbyte in range(JOINT_ENABLE_BYTES):
                data[bn] = 0xFF
                bn += 1

            # dout
            for dbyte in range(DIGITAL_OUTPUT_BYTES):
                data[bn] = douts[dbyte]
                bn += 1

            print("tx:", data)
            start = time.time()
            if NET_IP:
                UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                UDPClientSocket.sendto(bytes(data), (NET_IP, NET_PORT))
                UDPClientSocket.settimeout(0.2)
                msgFromServer = UDPClientSocket.recvfrom(len(data))
                rec = list(msgFromServer[0])
            elif SERIAL:
                ser.write(bytes(data))
                msgFromServer = ser.read(len(data))
                rec = list(msgFromServer)
            else:
                rec = spi.xfer2(data)

            print(f"Duration: {(time.time() - start):0.5f}")
            print("rx:", rec)

            jointFeedback = [0] * JOINTS
            processVariable = [0] * VINS

            pos = 0
            header = unpack('<i', bytes(rec[pos:pos+4]))[0]
            pos += 4

            for num in range(JOINTS):
                jointFeedback[num] = unpack('<i', bytes(rec[pos:pos+4]))[0]
                pos += 4

            for num in range(VINS):
                processVariable[num] = unpack('<i', bytes(rec[pos:pos+4]))[0]
                pos += 4

            inputs = []
            for dbyte in range(DIGITAL_INPUT_BYTES):
                inputs.append(unpack('<B', bytes(rec[pos:pos+1]))[0])
                pos += 1

            if header == 0x64617461:
                print(f'PRU_DATA: 0x{header:x}')
                for num in range(JOINTS):
                    print(f' Joint({num}): {jointFeedback[num]} // 1')
                for num in range(VINS):
                    print(f' Var({num}): {processVariable[num]}')
                #print(f'inputs {inputs:08b}')
            else:
                print(f'ERROR: Unknown Header: 0x{header:x}')
                self.error_counter_spi += 1

            for jn, value in enumerate(joints):
                key = f"jf{jn}"
                self.widgets[key].setText(str(jointFeedback[jn]))

            for vn in range(VINS):
                key = f"vi{vn}"
                unit = ""
                value = processVariable[vn]
                if vinminmax[vn][2] == 'frequency':
                    unit = "Hz"
                    if value != 0:
                        value = PRU_OSC / value
                elif vinminmax[vn][2] == 'pwm':
                    unit = "ms"
                    if value != 0:
                        value = 1000 / (PRU_OSC / value)
                elif vinminmax[vn][2] == 'sonar':
                    unit = "mm"
                    if value != 0:
                        value = 1000 / PRU_OSC / 20 * value * 343.2
                self.widgets[key].setText(f"{round(value, 2)}{unit}")

            for dbyte in range(DIGITAL_INPUT_BYTES):
                for dn in range(8):
                    key = f"dic{dbyte}{dn}"

                    value = "0"
                    if inputs[dbyte] & (1<<dn) != 0:
                        value = "1"

                    self.widgets[key].setText(value)
                    if value == "0":
                        self.widgets[key].setStyleSheet("background-color: lightgreen")
                    else:
                        self.widgets[key].setStyleSheet("background-color: yellow")

                    if dbyte * 8 + dn == DINS - 1:
                        break

        except Exception as e:
            print("ERROR", e)
            self.error_counter_net += 1

        self.widgets["errors_spi"].setText(str(self.error_counter_spi))
        self.widgets["errors_net"].setText(str(self.error_counter_net))


if __name__ == '__main__':
    app=QApplication(sys.argv)
    form=WinForm()
    form.show()
    sys.exit(app.exec_())


    