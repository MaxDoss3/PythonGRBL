Python GRBL Serial sending utility for CNC Routers. Features the ability to send G code, $J bounds checking, 
as well a way to automatically search a field with a mounted webcam for a QR code. Once a QR is found it 
will center the QR in the frame

## Quick Start

Installing requirements:

```bash
pip install zbar
```

```bash
pip install opencv-python
```

Used for QR detection paired with OpenCV

```bash
pip install pyserial
```

For serial interaction between python and the GRBL controller

To run: python serial_test.py
