#include <assert.h>
#include "shader_layer.c"

static const VkInstanceCreateInfo *expected_info;
static const VkAllocationCallbacks *expected_allocator;
static VkResult downstream_result;
static unsigned forwarded;

static VkResult VKAPI_CALL mock_create(const VkInstanceCreateInfo *info,
    const VkAllocationCallbacks *allocator, VkInstance *instance) {
    assert(info == expected_info);
    assert(allocator == expected_allocator);
    assert(instance != NULL);
    forwarded++;
    return downstream_result;
}

static PFN_vkVoidFunction VKAPI_CALL mock_proc(VkInstance instance, const char *name) {
    assert(instance == VK_NULL_HANDLE);
    assert(!strcmp(name, "vkCreateInstance"));
    return (PFN_vkVoidFunction)mock_create;
}

int main(void) {
    VkApplicationInfo app = {.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
        .pApplicationName = "gamescope", .apiVersion = VK_API_VERSION_1_3};
    const char *extensions[] = {"VK_KHR_surface", "VK_KHR_wayland_surface"};
    VkLayerInstanceLink link = {.pfnNextGetInstanceProcAddr = mock_proc};
    VkLayerInstanceCreateInfo chain = {.sType = VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO,
        .function = VK_LAYER_LINK_INFO, .u.pLayerInfo = &link};
    VkInstanceCreateInfo info = {.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
        .pNext = &chain, .pApplicationInfo = &app, .enabledExtensionCount = 2,
        .ppEnabledExtensionNames = extensions};
    VkInstance instance = VK_NULL_HANDLE;
    expected_info = &info;
    downstream_result = VK_NOT_READY;
    assert(create_instance(&info, NULL, &instance) == VK_NOT_READY);
    assert(chain.u.pLayerInfo == NULL);
    assert(forwarded == 1);
    VkAllocationCallbacks allocator = {0};
    expected_allocator = &allocator;
    chain.u.pLayerInfo = &link;
    downstream_result = VK_ERROR_INCOMPATIBLE_DRIVER;
    assert(create_instance(&info, &allocator, &instance) == VK_ERROR_INCOMPATIBLE_DRIVER);
    assert(forwarded == 2);
    return 0;
}
