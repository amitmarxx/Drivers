from mesa_edit import replace

# Experiment for intermittent black / half-drawn frames on screen (Adreno 740, KGSL 5.15).
# vkQueueSignalReleaseImageANDROID submits the present wait and immediately exports the release
# semaphore as a sync file. On KGSL, exporting a syncobj whose submit has not reached the kernel
# yet (threaded submit, emulated timelines) returns -1, which Android treats as "already
# signalled": SurfaceFlinger / the display can read the swapchain image while the GPU is still
# writing it. This test build waits for the queue to go idle before handing the image to Android,
# so the -1 it returns is true.

ANDROID = 'src/vulkan/runtime/vk_android.c'

replace(
    ANDROID,
    '#include "util/os_file.h"\n',
    '#include "util/os_file.h"\n#include <unistd.h>\n',
    'unistd include for the release wait',
)

replace(
    ANDROID,
    '   STACK_ARRAY_FINISH(wait_infos);\n'
    '   if (result != VK_SUCCESS)\n'
    '      return result;\n'
    '\n'
    '   const VkSemaphoreGetFdInfoKHR get_fd = {\n'
    '      .sType = VK_STRUCTURE_TYPE_SEMAPHORE_GET_FD_INFO_KHR,\n'
    '      .handleType = VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT,\n'
    '      .semaphore = queue->anb_semaphore,\n'
    '   };\n'
    '   return device->dispatch_table.GetSemaphoreFdKHR(vk_device_to_handle(device),\n'
    '                                                   &get_fd, pNativeFenceFd);\n',
    '   STACK_ARRAY_FINISH(wait_infos);\n'
    '   if (result != VK_SUCCESS)\n'
    '      return result;\n'
    '\n'
    '   const VkSemaphoreGetFdInfoKHR get_fd = {\n'
    '      .sType = VK_STRUCTURE_TYPE_SEMAPHORE_GET_FD_INFO_KHR,\n'
    '      .handleType = VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT,\n'
    '      .semaphore = queue->anb_semaphore,\n'
    '   };\n'
    '   /* DroidDeck test: export (which resets the binary semaphore), then make the image really\n'
    '    * finished before Android sees it. */\n'
    '   int dd_fd = -1;\n'
    '   result = device->dispatch_table.GetSemaphoreFdKHR(vk_device_to_handle(device),\n'
    '                                                     &get_fd, &dd_fd);\n'
    '   if (dd_fd >= 0)\n'
    '      close(dd_fd);\n'
    '   if (result != VK_SUCCESS)\n'
    '      return result;\n'
    '   result = device->dispatch_table.QueueWaitIdle(_queue);\n'
    '   static bool dd_logged;\n'
    '   if (!dd_logged) {\n'
    '      dd_logged = true;\n'
    '      mesa_logi("DroidDeck test: release image waits for queue idle (exported fd was %d)", dd_fd);\n'
    '   }\n'
    '   *pNativeFenceFd = -1;\n'
    '   return result;\n',
    'release image waits for the queue',
)

# Second experiment in the same build: before DroidDeck may draw into a swapchain image again, wait
# on the CPU for Android's release fence (SurfaceFlinger / display done reading it), in case the
# GPU-side wait on the imported sync file is not honoured on KGSL.
replace(
    ANDROID,
    '   int semaphore_fd = -1, fence_fd = -1;\n'
    '   if (nativeFenceFd >= 0) {\n',
    '   int semaphore_fd = -1, fence_fd = -1;\n'
    '   if (nativeFenceFd >= 0) {\n'
    '      static bool dd_acq_logged;\n'
    '      int dd_ret = sync_wait(nativeFenceFd, 1000);\n'
    '      if (!dd_acq_logged) {\n'
    '         dd_acq_logged = true;\n'
    '         mesa_logi("DroidDeck test: acquire waits for the release fence on the CPU (sync_wait %d)", dd_ret);\n'
    '      }\n',
    'acquire waits for the Android release fence on the CPU',
)
