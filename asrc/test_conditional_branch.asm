ADD R2, R2, 0x18
ADD R0, R0, 0x14
ADD R1, R1, 0x1
ADD R3, R3, 0x5
ADD R4, R4, 0x5
ADD R25, R25, R3
ADD R2, R2, R1
CMP R25, R0
BLE [R3]
END