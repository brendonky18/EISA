# Table of Contents <!-- omit in toc -->

- [System Design](#system-design)
- [TODO:](#todo)
  - [Memory and Cache Demo](#memory-and-cache-demo)
  - [Partial Simulation](#partial-simulation)
  - [Full ISA](#full-isa)
  - [GUI](#gui)

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
 - [ ] Implement Memory
 - [ ] Implement unified cache
   - [ ] Implement Load/Store from memory
     - Must record time taken for operation
   - [ ] Function to enable/disable cache
 - [ ] Implement terminal interface
   - [ ] Read from memory
   - [ ] Read to memory
   - [ ] Display contents from memory
   - [ ] Specify size for cache and memory

## Partial Simulation
 - [ ] Minimal instruction set implementation
 - [ ] Working assembler
 - [ ] Full GUI

## Full ISA
 - [ ] Implement AES instructions

## GUI
 - [ ] Able to view and manipualte registers