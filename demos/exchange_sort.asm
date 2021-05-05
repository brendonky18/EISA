PUSH r0 ; array length
PUSH r1 ; i
PUSH r2 ; j
PUSH r3 ; temp
LDR r0, #21
MOV r1, 0 ; i = 0
CMP r1, r0 ; start of outer loop
BLT #20 ; i < len, branch to end of outer loop
ADD r2, r1, 1 ; j = i + 1
CMP r2, r0; start of inner loop
BLT #19 ; j < len, branch to end of inner loop
LDR r4, [r1, #20] ; array[i]
LDR r5, [r2, #20] ; array[j]
CMP r4, r5 ; if r5 > r4
BGT #9 ; start of inner loop 
MOV r3, r4 ; temp = array[i]
STR r5, [r1, #20] ; array[i] = array[j]
STR r3, [r2, #20] ; array[j] = temp
B #9 ; end of inner loop, branch to start of inner loop
B #6 ; end of outer loop, branch to start of outer loop
END
