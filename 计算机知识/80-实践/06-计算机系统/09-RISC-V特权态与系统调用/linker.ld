OUTPUT_ARCH(riscv)
ENTRY(_start)

SECTIONS
{
  . = 0x80000000;

  .text : ALIGN(4096) {
    KEEP(*(.text.start))
    KEEP(*(.text.trap))
    *(.text .text.*)
  }

  .rodata : ALIGN(16) {
    *(.rodata .rodata.*)
  }

  .data : ALIGN(16) {
    *(.data .data.*)
  }

  .bss (NOLOAD) : ALIGN(16) {
    __bss_start = .;
    *(.bss .bss.* COMMON)
    . = ALIGN(16);
    m_stack_bottom = .;
    . += 4096;
    m_stack_top = .;
    s_stack_bottom = .;
    . += 8192;
    s_stack_top = .;
    user_stack_bottom = .;
    . += 4096;
    user_stack_top = .;
    . = ALIGN(16);
    trapframe_area = .;
    . += 272;
    __bss_end = .;
  }

  kernel_end = .;

  /DISCARD/ : {
    *(.comment)
    *(.eh_frame .eh_frame.*)
  }
}
