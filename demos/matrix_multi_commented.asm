; Remaining registers - R9, R10

ADD R0, R0, 0x32 ; Num rows
ADD R1, R1, 0x32 ; Num cols
ADD R9, R9, 0x32
SUB R9, R9, 0x1
MULT R9, R9, R1  ; Build the column resetter ((n-1)*n)

; Matrix A
ADD R2, R2, 0x0  ; Row counter A
ADD R3, R3, 0x0  ; Col counter A
ADD R4, R4, 0x32  ; Address counter A

; Matrix B
ADD R5, R5, 0x0 ; Row counter B
ADD R6, R6, 0x0 ; Col counter B
ADD R7, R7, 0x9f6 ; Address counter B

; Matrix C (Product Matrix)
ADD R8, R8, 0x13ba ; Address counter C
ADD R13, R13, 0x0 ; Sum register

; Load operands
LDR R11, R4, R28 ; Load next Matrix A val into R11
LDR R12, R7, R28 ; Load next Matrix B val into R12

; Multiply operands
MULT R14, R11, R12 ; Temp reg to store product

; Accumlate products
ADD R13, R13, R14  ; Add the temp product to the total sum to work towards final value

; Increment address counters
ADD R4, R4, 0x1  ; Add 1 to the address counter A because matrix A is processed sequentially
ADD R7, R7, R1  ; Add m (column space) to address counter B to goto next row

; Increment row and col counters
ADD R3, R3, #0x1  ; Increment col counter A
ADD R5, R5, #0x1  ; Increment row counter B

; Compare whether row iterator is less than the total num of columns
CMP R3, R1  ; Compare col counter A to total num of columns
BLT R28, #0xc  ; Branch to 12th line to continue processing the curr row and col (R28 is 0 register)

; Reset counters
SUB R4, R4, R1  ; Subtract number of columns from address counter A to go back to beginning of row
SUB R7, R7, R9  ; Subtract address counter B by the column resetter register to get back to the correct row
ADD R7, R7, 0x1  ; Increment address counter B by 1 to get to next column
ADD R6, R6, 0x1  ; Increment column counter B
SUB R3, R3, R3  ; Reset col counter A
SUB R5, R5, R5  ; Reset row counter B

STR R13, R8  ; Store the sum-product of the current position
ADD R8, R8, 0x1  ;  Increment address counter C
SUB R13, R13, R13  ; Reset sum-product position register

CMP R6, R1  ; Compare column counter B to total number of columns
BLT  ; Branch back to load statements to process the next position of matrix C in the row

; At this point, an entire row of matrix C has been processed

ADD R2, R2, 0x1  ; Increment row counter A to goto next row of matrix A
SUB R6, R6, R6  ; Reset column counter B to start at column 0
SUB R7, R7, R9  ; Reset address counter B to start at column 0
ADD R4, R4, R1  ; Add number of columns to address counter A to go to next row

BLT  ; Branch back to start if there's more rows to be processed (row counter A < total num of cols)

END