# Table of Contents <!-- omit in toc -->

- [System Design](#system-design)
- [TODO:](#todo)
  - [Memory and Cache Demo](#memory-and-cache-demo)
  - [Second Memory Demo](#second-memory-demo)
  - [Partial Simulation](#partial-simulation)
  - [Full ISA](#full-isa)
  - [GUI](#gui)
  - [Speculative Execution/Reorder Buffer](#speculative-executionreorder-buffer)
    - [Pipeline w/ Spec Ex](#pipeline-w-spec-ex)

# System Design
 - Extension for RISC ISA to implement hardware acceleration for AES
 - Targeted for embedded devices (like routers)
 - 32 bit word size
 - Registers
   - 32 bit GP registers
   - 128 bit SP registers for AES keys
   - 256 bit SP registers for hashes

# TODO:

## Memory and Cache Demo
- Memory subsystem minimum requirements
   -  Unified cache
   -  Write-through
   -  Direct-mapped
   -  No allocate
   -  4 words per line
 - [ ] Implement Clock
   - Loop with callback function that is executed every cycle
 - [ ] Implement memory device interface
 - [ ] Implement external memory
 - [ ] Implement unified cache
   - [ ] Implement Load/Store from memory
     - Must record time taken for operation
   - [ ] Function to enable/disable cache
 - [ ] Implement terminal interface
   - [ ] Read from memory
   - [ ] Read to memory
   - [ ] Display contents from memory
   - [ ] Specify size for cache and memory

Planning:
- [ ] Memory subsystem:
  - [x] init
    - [x] instantiate cache
    - [x] instantiate ram
  - [ ] read: (read through policy)
    - [x] cache read policy
      - [x] if hit
        - [x] read the value from cache
      - [x] if miss
        - [x] read block from RAM
          - TODO: 
        - [x] write new values to cache
          - [x] evict the old cache way 
          - [x] replace it with the new data
        - [x] read the value from the updated cache
    - [ ] RAM read policy
      - [ ] return the value at the address, cannot miss
  - [ ] write: (write through, no-write allocate policy)
    - [x] cache write policy
      - [x] if hit:
        - [x] write the value to cache
        - [x] policy-write the value to RAM
      - [x] if miss:
        - [x]  policy-write the value to RAM
    - [ ]  RAM write policy
      - [ ]  write the value, cannot miss
- [ ] Cache: 
  - [x] read: 
    - [x] check if the address is in the cache
      - [x] get the index and tag from the address
      - [x] get the cache way at the corresponding index
      - [x] check if the tags match
        - [x] if tags match (cache hit)
          - [x] return the value
        - [x] if tags don't macth (cache miss)
          - [x] raise exception
  - [ ] write: 
    - [ ] check if the address is in the cache
      - [x] get the index and tag from the address
      - [x] get the cache way at the corresponding index
      - [x] check if the tags match
        - [x] if tags match (cache hit)
          - [x] write the value to the cache
        - [x] if tags don't match (cache miss)
          - [x] replace the value 
  - [x] replace
    - [x] evict the current value
    - [x] update the tag
    - [x] update the data
- [x] RAM:
  - [x] read:
    - [x] get the value and return it
  - [x] write:
    - [x] write the value

- [ ] Update documentation

## Second Memory Demo
  - [ ] Fix issues with improper formating in cache
  - [ ] Clock changes
    - [ ] Make clock faster
    - [ ] print delays in cycles rather than ms

## Partial Simulation
 - [ ] Minimal instruction set implementation
 - [ ] Working assembler
 - [ ] Full GUI
 - [ ] Add masking constant to EISA
   - EISA.X_MASK = EISA.X_SIZE - 1

## Full ISA
 - [ ] Implement AES instructions

## GUI
 - [ ] Able to view and manipualte registersz

## Speculative Execution/Reorder Buffer
 - FIFO queue of speculative executions
 - When speculatively executing an instruction, it is placed in the ROB
 - Each ROB entry has 4 fields
    - Instruction type: 
    - (ALU, load, store, branch)
    - Instruction destination 
      - Where the result of the instruction will be written
      - Destination register, memory address
    - Ready flag
      - Binary indication if the instruction has completed execution or not
    - Value field
      - Contains the result calculated by computing the instruction
 - When the hazard has cleared, if the prediction is correct, the instructions from the ROB can be retired, ie. committed
 - Instructions in the ROB cannot change the state
   - Cannot write to registers
   - Cannot write to memory
 - They can READ from memory however

### Pipeline w/ Spec Ex
 - Fetch
   - Place instruction in ROB
 - Execute/Memory Read
   - Write result to ROB
 - Writeback/Memory Write
   - Retire the instruction if its ready
   - For conditional branches, if branch result is incorrect, flush the ROB and fetch correct instruction.

