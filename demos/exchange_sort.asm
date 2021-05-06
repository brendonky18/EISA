PUSH r0 ; array length
PUSH r1 ; i
PUSH r2 ; j
PUSH r3 ; temp
LDR r0, #23
MOV r1, 0 ; i = 0
CMP r1, r0 ; start of outer loop
BGE #22 ; i < len, branch to end of outer loop
ADD r2, r1, 1 ; j = i + 1
CMP r2, r0; start of inner loop
BGE #20 ; j < len, branch to end of inner loop
LDR r4, [r1, #24] ; array[i]
LDR r5, [r2, #24] ; array[j]
CMP r4, r5 ; if array[i] < array[j]
BLT #18 ; start of inner loop 
MOV r3, r4 ; temp = array[i]
STR r5, [r1, #24] ; array[i] = array[j]
STR r3, [r2, #24] ; array[j] = temp
ADD r2, r2, 1 ; j++
B #9 ; end of inner loop, branch to start of inner loop
ADD r1, r1, 1 ; i++
B #6 ; end of outer loop, branch to start of outer loop
END
