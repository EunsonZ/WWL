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
  ASSERT(. <= 0x80010000, "kernel image overlaps the fixed user code page")

  . = 0x80010000;
  .user_text : { KEEP(*(.user.text)) }
  ASSERT(. <= 0x80011000, "user code exceeds one page")

  . = 0x80011000;
  .user_data : { KEEP(*(.user.data)) }
  ASSERT(. <= 0x80012000, "user data exceeds one page")

  . = 0x80012000;
  .user_nx : { KEEP(*(.user.nx)) }
  ASSERT(. <= 0x80013000, "user NX sample exceeds one page")

  . = 0x80013000;
  .kernel_secret : { KEEP(*(.kernel.secret)) }
  ASSERT(. <= 0x80014000, "kernel secret exceeds one page")

  . = 0x80014000;
  .bss (NOLOAD) : {
    __bss_start = .;
    *(.bss .bss.* COMMON)
    . = 0x80015000;
    user_stack_bottom = .;
    . += 4096;
    user_stack_top = .;
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
    trapframe_area = .;
    . += 4096;
    m_stack_bottom = .;
    . += 4096;
    m_stack_top = .;
    s_stack_bottom = .;
    . += 8192;
    s_stack_top = .;
    __bss_end = .;
  }
  ASSERT(. == 0x8001f000, "fixed physical layout changed")
  kernel_end = .;

  /DISCARD/ : {
    *(.comment)
    *(.eh_frame .eh_frame.*)
    *(.riscv.attributes)
  }
}
