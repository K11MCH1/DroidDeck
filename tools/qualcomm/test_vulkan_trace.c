#define DROIDDECK_VK_TRACE_TEST
#define getuid dd_test_getuid
static unsigned dd_test_getuid(void) { return 10458; }
#include "vulkan_trace.c"
#include <assert.h>

static int return_code, created, destroyed, platform_tag;
static VkResult VKAPI_CALL mock_version(uint32_t *value) {
    *value = VK_API_VERSION_1_4;
    return return_code;
}
static VkResult VKAPI_CALL mock_platform_version(uint32_t *value) {
    *value = VK_API_VERSION_1_4;
    return VK_SUCCESS;
}
static VkResult VKAPI_CALL mock_create(const VkInstanceCreateInfo *info,
    const VkAllocationCallbacks *allocator, VkInstance *instance) {
    assert(info->pNext == NULL && !info->enabledExtensionCount && !info->enabledLayerCount);
    assert(allocator == NULL);
    created++;
    *instance = (VkInstance)(uintptr_t)123;
    return return_code;
}
static void VKAPI_CALL mock_destroy(VkInstance instance, const VkAllocationCallbacks *allocator) {
    assert(instance == (VkInstance)(uintptr_t)123 && allocator == NULL);
    destroyed++;
}
static PFN_vkVoidFunction VKAPI_CALL mock_gipa(VkInstance instance, const char *name) {
    if (!strcmp(name, "vkEnumerateInstanceVersion")) return (void *)mock_version;
    if (!strcmp(name, "vkCreateInstance")) return (void *)mock_create;
    if (!strcmp(name, "vkDestroyInstance") && instance) return (void *)mock_destroy;
    return NULL;
}
static PFN_vkVoidFunction VKAPI_CALL mock_platform_gipa(VkInstance instance, const char *name) {
    if (!strcmp(name, "vkEnumerateInstanceVersion")) return (void *)mock_platform_version;
    return mock_gipa(instance, name);
}
static struct dd_hw_vulkan device = {
    .common = {.tag = 0x48574454, .version = 0x10000}, .create = mock_create, .get = mock_gipa};
static int mock_hal_open(const struct dd_hw_module *module, const char *id, struct dd_hw_device **out) {
    assert(module && !strcmp(id, "vk0"));
    *out = &device.common;
    return 0;
}
static struct dd_hw_methods methods = {.open = mock_hal_open};
static struct dd_hw_module module = {.tag = 0x48574d54, .id = "vulkan", .methods = &methods};
static void *mock_open(const char *path, int flags) {
    assert(flags == 2);
    if (!strcmp(path, "/vendor/lib64/hw/vulkan.adreno.so")) return &module;
    if (!strcmp(path, "/system/lib64/libvulkan.so")) return &platform_tag;
    return NULL;
}
static void *mock_symbol(void *library, const char *name) {
    if (!strcmp(name, "HMI") && library == &module) return &module;
    if (!strcmp(name, "vkGetInstanceProcAddr")) return (void *)mock_platform_gipa;
    if (!strcmp(name, "vkEnumerateInstanceVersion"))
        return library == &module ? (void *)mock_version : (void *)mock_platform_version;
    return NULL;
}
static int mock_address(const void *pointer, struct dd_dl_info *info) {
    assert(pointer != NULL);
    *info = (struct dd_dl_info){.file = "mock\\module\"name\n.so", .symbol = "test", .base = (void *)16};
    return 1;
}
static const char *mock_error(void) { return "test loader"; }

int main(int argc, char **argv) {
    assert(argc == 3);
    return_code = atoi(argv[2]);
    int result = dd_vulkan_trace("host-test", argv[1], 3, mock_open, mock_symbol, mock_address, mock_error);
    if (strcmp(argv[1], "platform")) assert(!created && !destroyed);
    else {
        assert(created == 1);
        assert(destroyed == (return_code == 0 ? 1 : 0));
    }
    return result;
}
