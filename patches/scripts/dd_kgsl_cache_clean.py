from mesa_edit import replace

# Experiment for black / half-drawn frames shared between processes on KGSL (Adreno 740, kernel 5.15).
# tu_EndCommandBuffer cleans CCU and relies on the kernel to clean UCHE after every submit, which the
# msm kernel does. If KGSL does not, a frame's last writes can stay dirty in UCHE (or the A7XX blit
# cache) while another process starts reading or invalidating, and the reader gets black or partial
# content. DD_TU_KGSL_FLUSH selects the fix (default 3; 0 = stock behaviour):
#   bit 0: at the end of every command buffer also clean UCHE and the blit cache, then wait for memory
#          writes and idle, so the work is in memory before the submit completes
#   bit 1: clean UCHE before every UCHE invalidate

CMD = 'src/freedreno/vulkan/tu_cmd_buffer.cc'

replace(
    CMD,
    'template <chip CHIP>\nstatic void\ntu6_emit_flushes(struct tu_cmd_buffer *cmd_buffer,',
    '#include <cstdlib>\n'
    '\n'
    'static unsigned\n'
    'dd_kgsl_flush_mode(void)\n'
    '{\n'
    '   static int mode = -1;\n'
    '   if (mode < 0) {\n'
    '      const char *s = std::getenv("DD_TU_KGSL_FLUSH");\n'
    '      mode = s ? atoi(s) : 3;\n'
    '      mesa_logi("DD_TU_KGSL_FLUSH=%d (1: clean UCHE at command buffer end, 2: clean before UCHE invalidate)", mode);\n'
    '   }\n'
    '   return (unsigned) mode;\n'
    '}\n'
    '\n'
    'template <chip CHIP>\nstatic void\ntu6_emit_flushes(struct tu_cmd_buffer *cmd_buffer,',
    'DD_TU_KGSL_FLUSH mode helper',
)

replace(
    CMD,
    '   if (TU_DEBUG(FLUSHALL))\n'
    '      flushes |= TU_CMD_FLAG_ALL_CLEAN | TU_CMD_FLAG_ALL_INVALIDATE;\n',
    '   if (TU_DEBUG(FLUSHALL))\n'
    '      flushes |= TU_CMD_FLAG_ALL_CLEAN | TU_CMD_FLAG_ALL_INVALIDATE;\n'
    '\n'
    '   if ((dd_kgsl_flush_mode() & 2) && (flushes & TU_CMD_FLAG_CACHE_INVALIDATE))\n'
    '      flushes |= TU_CMD_FLAG_CACHE_CLEAN;\n',
    'clean UCHE before invalidating it',
)

replace(
    CMD,
    '      tu_clean_all_pending(&cmd_buffer->state.cache);\n'
    '      cmd_buffer->state.cache.flush_bits |=\n'
    '         TU_CMD_FLAG_CCU_CLEAN_COLOR |\n'
    '         TU_CMD_FLAG_CCU_CLEAN_DEPTH;\n',
    '      tu_clean_all_pending(&cmd_buffer->state.cache);\n'
    '      cmd_buffer->state.cache.flush_bits |=\n'
    '         TU_CMD_FLAG_CCU_CLEAN_COLOR |\n'
    '         TU_CMD_FLAG_CCU_CLEAN_DEPTH;\n'
    '      if (dd_kgsl_flush_mode() & 1)\n'
    '         cmd_buffer->state.cache.flush_bits |=\n'
    '            TU_CMD_FLAG_CACHE_CLEAN |\n'
    '            TU_CMD_FLAG_BLIT_CACHE_CLEAN |\n'
    '            TU_CMD_FLAG_WAIT_MEM_WRITES |\n'
    '            TU_CMD_FLAG_WAIT_FOR_IDLE;\n',
    'clean UCHE and the blit cache at command buffer end',
)
