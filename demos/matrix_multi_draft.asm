; Remaining registers - R9, R10

ADD R0, R0, 0x32 ; Num rows
ADD R1, R1, 0x32 ; Num cols

; Matrix A
ADD R2, R2, 0x0  ; Row counter A
ADD R3, R3, 0x0  ; Col counter A
ADD R4, R4, 0x0  ; Address counter A

; Matrix B
ADD R5, R5, 0X0 ; Row counter B
ADD R6, R6, 0X0 ; Col counter B
ADD R7, R7, 0x9c4 ; Address counter B

; Matrix C (Product Matrix)
ADD R8, R8, 0x1388 ; Address counter C
ADD R13, R13, 0X0 ; Sum register

; Load operands
LDR R11, R4, #0x0 ; Load next Matrix A val into R11
LDR R12, R7, #0x0 ; Load next Matrix B val into R12
; Multiply operands
MULT R14, R11, R12 ; Temp reg to store product
; Accumlate products
ADD R13, R13, R14  ; Add the temp product to the total sum to work towards final value
; Increment address counters
ADD R4, R4, 0x1  ; Add 1 to the address counter A because matrix A is processed sequentially
ADD R7, R7, R1  ; Add m (column space) to address counter B to goto next row
; Increment row/col counters
ADD R3, R3, 0x1  ; Increment col position A by 1
ADD R5, R5, 0x1  ; Increment row position B by 1
CMP R3, R1  ; Compare col counter A to total num of columns
BLT R28, #0xc  ; Branch to 12th line to continue processing the curr row and col (R28 is 0 register)
;  If it makes it past that branch, then we know the curr pos is done processing
ADD R2, R2, 0x1  ; Increment row position A by 1  ; Increment row pos A by 1
ADD R6, R6, 0x1  ; Increment col position B by 1  ; Increment col pos B by 1
SUB R3, R3, R3  ; Reset col position A to 0
SUB R5, R5, R5  ; Reset row position B to 0
STR R13, R8, #0x0  ; Set the next value of C
ADD R8, R8, 0x1  ; Increment address counter for matrix C (storing sequentially [rows])
SUB R13, R13, R13  ; Reset product/sum register
CMP R2, R0  ; Compare row counter A to total num of rows
BLT R28, #0xc ; Branch back to start if R2 < R0
END