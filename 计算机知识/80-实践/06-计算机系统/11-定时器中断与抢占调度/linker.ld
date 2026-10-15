OUTPUT_ARCH(riscv)
ENTRY(_start)

SECTIONS
{
  . = 0x80000000;
  .text : {
    KEEP(*(.text.start))
    KEEP(*(.text.trap))
    *(.text .text.*)
  }
  .rodata : ALIGN(16) { *(.rodata .rodata.*) }
  .data : ALIGN(16) { *(.data .data.*) }
  .bss (NOLOAD) : ALIGN(16) {
    __bss_start = .;
    *(.bss .bss.* COMMON)
    __bss_end = .;
  }
  ASSERT(. <= 0x80010000, "kernel image overlaps user task 0")

  . = 0x80010000;
  .user0_text : { KEEP(*(.user0.text)) }
  ASSERT(. <= 0x80011000, "user task 0 exceeds one page")

  . = 0x80011000;
  .user_data : { KEEP(*(.user.data)) }
  ASSERT(. <= 0x80012000, "user data exceeds one page")

  . = 0x80012000;
  .user1_text : { KEEP(*(.user1.text)) }
  ASSERT(. <= 0x80013000, "user task 1 exceeds one page")

  . = 0x80013000;
  .runtime (NOLOAD) : {
    __runtime_start = .;
    task0_stack_bottom = .;
    . += 4096;
    task0_stack_top = .;
    task1_stack_bottom = .;
    . += 4096;
    task1_stack_top = .;
    root_page_table = .;
    . += 4096;
    user_l1_page_table = .;
    . += 4096;
    user_l0_page_table = .;
    . += 4096;
    kernel_l1_page_table = .;
    . += 4096;
    kernel_l0_page_table = .;
    . += 4096;
    task0_trapframe = .;
    . += 4096;
    task1_trapframe = .;
    . += 4096;
    m_stack_bottom = .;
    . += 4096;
    m_stack_top = .;
    s_stack_bottom = .;
    . += 8192;
    s_stack_top = .;
    __runtime_end = .;
  }
  ASSERT(. == 0x8001f000, "fixed physical layout changed")
  kernel_end = .;

  /DISCARD/ : {
    *(.comment)
    *(.eh_frame .eh_frame.*)
    *(.riscv.attributes)
  }
}
