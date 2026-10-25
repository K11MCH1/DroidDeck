#define _GNU_SOURCE
#define VK_NO_PROTOTYPES
#include "hal_probe_abi.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct dd_dl_info {
    const char *file;
    void *base;
    const char *symbol;
    void *symbol_address;
};
struct dd_loader {
    void *(*open)(const char *, int);
    void *(*symbol)(void *, const char *);
    int (*address)(const void *, struct dd_dl_info *);
    const char *(*error)(void);
};

static void quoted(const char *text) {
    putchar('"');
    for (const unsigned char *p = (const void *)(text ? text : ""); *p; p++) {
        if (*p == '"' || *p == '\\') printf("\\%c", *p);
        else if (*p < 32) printf("\\u%04x", *p);
        else putchar(*p);
    }
    putchar('"');
}

static void owner(struct dd_loader *loader, const char *name, const void *pointer) {
    struct dd_dl_info info = {0};
    int found = pointer && loader->address && loader->address(pointer, &info);
    printf("{\"event\":\"function.resolved\",\"name\":"); quoted(name);
    printf(",\"address\":\"%p\",\"owner_found\":%s,\"module\":", pointer, found ? "true" : "false");
    quoted(found ? info.file : "");
    printf(",\"symbol\":"); quoted(found ? info.symbol : "");
    printf(",\"module_offset\":\"0x%" PRIxPTR "\"}\n",
           found ? (uintptr_t)pointer - (uintptr_t)info.base : 0);
    fflush(stdout);
}

static void failure(struct dd_loader *loader, const char *operation) {
    printf("{\"event\":\"trace.error\",\"operation\":"); quoted(operation);
    printf(",\"error\":"); quoted(loader->error ? loader->error() : "unavailable");
    printf("}\n"); fflush(stdout);
}

static int version_query(struct dd_loader *loader, const char *name, PFN_vkVoidFunction address) {
    owner(loader, name, (const void *)address);
    if (!address) return 2;
    uint32_t value = 0xa850a850;
    printf("{\"event\":\"version.calling\",\"source\":"); quoted(name);
    printf(",\"initial_raw\":%u}\n", value); fflush(stdout);
    VkResult result = ((PFN_vkEnumerateInstanceVersion)address)(&value);
    printf("{\"event\":\"version.result\",\"source\":"); quoted(name);
    printf(",\"result\":%d,\"raw\":%u,\"written\":%s,\"version\":\"%u.%u.%u\"}\n",
        result, value, value != 0xa850a850 ? "true" : "false",
        VK_API_VERSION_MAJOR(value), VK_API_VERSION_MINOR(value), VK_API_VERSION_PATCH(value));
    fflush(stdout);
    return result == VK_SUCCESS && value != 0xa850a850 ? 0 : 1;
}

static void *platform_loader(struct dd_loader *loader) {
    void *library = loader->open("/system/lib64/libvulkan.so", 2);
    if (!library) failure(loader, "open Android Vulkan loader");
    return library;
}

static int platform_probe(struct dd_loader *loader, uint32_t minor) {
    void *library = platform_loader(loader);
    if (!library) return 2;
    PFN_vkGetInstanceProcAddr get = (void *)loader->symbol(library, "vkGetInstanceProcAddr");
    owner(loader, "platform.vkGetInstanceProcAddr", (const void *)get);
    if (!get) return 2;
    version_query(loader, "platform.gipa.vkEnumerateInstanceVersion", get(0, "vkEnumerateInstanceVersion"));
    PFN_vkVoidFunction exported = loader->symbol(library, "vkEnumerateInstanceVersion");
    version_query(loader, "platform.export.vkEnumerateInstanceVersion", exported);
    PFN_vkCreateInstance create = (void *)get(0, "vkCreateInstance");
    owner(loader, "platform.gipa.vkCreateInstance", (const void *)create);
    if (!create) return 2;
    VkApplicationInfo app = {.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
        .pApplicationName = "gamescope", .applicationVersion = VK_MAKE_VERSION(1, 0, 0),
        .pEngineName = "hopefully not just some code", .engineVersion = VK_MAKE_VERSION(1, 0, 0),
        .apiVersion = VK_MAKE_VERSION(1, minor, 0)};
    VkInstanceCreateInfo info = {.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &app};
    VkInstance instance = VK_NULL_HANDLE;
    printf("{\"event\":\"instance.calling\",\"api\":\"1.%u.0\",\"extensions\":[],\"layers\":[],\"pnext\":[]}\n", minor);
    fflush(stdout);
    VkResult result = create(&info, NULL, &instance);
    printf("{\"event\":\"instance.result\",\"result\":%d,\"handle_present\":%s}\n", result, instance ? "true" : "false");
    fflush(stdout);
    if (result != VK_SUCCESS || !instance) return 1;
    PFN_vkEnumeratePhysicalDevices enumerate = (void *)get(instance, "vkEnumeratePhysicalDevices");
    PFN_vkGetPhysicalDeviceProperties properties = (void *)get(instance, "vkGetPhysicalDeviceProperties");
    if (enumerate && properties) {
        VkPhysicalDevice device = VK_NULL_HANDLE;
        uint32_t count = 1;
        VkResult listed = enumerate(instance, &count, &device);
        if ((listed == VK_SUCCESS || listed == VK_INCOMPLETE) && count && device) {
            VkPhysicalDeviceProperties value;
            properties(device, &value);
            printf("{\"event\":\"physical.device\",\"name\":"); quoted(value.deviceName);
            printf(",\"api_raw\":%u,\"driver_raw\":%u,\"vendor\":%u}\n", value.apiVersion, value.driverVersion, value.vendorID);
        }
    }
    PFN_vkDestroyInstance destroy = (void *)get(instance, "vkDestroyInstance");
    owner(loader, "platform.gipa.vkDestroyInstance", (const void *)destroy);
    fflush(stdout);
    if (!destroy) return 2;
    destroy(instance, NULL);
    printf("{\"event\":\"instance.destroyed\"}\n"); fflush(stdout);
    return 0;
}

static void *hal_library(struct dd_loader *loader) {
    void *support = loader->open("/system/lib64/libvndksupport.so", 2);
    void *(*load_sphal)(const char *, int) = support ? loader->symbol(support, "android_load_sphal_library") : NULL;
    owner(loader, "android_load_sphal_library", (const void *)load_sphal);
    void *library = load_sphal ? load_sphal("/vendor/lib64/hw/vulkan.adreno.so", 2) : NULL;
    if (library) {
        printf("{\"event\":\"hal.load\",\"method\":\"android_load_sphal_library\"}\n");
    } else {
        if (load_sphal) failure(loader, "android_load_sphal_library");
        library = loader->open("/vendor/lib64/hw/vulkan.adreno.so", 2);
        printf("{\"event\":\"hal.load\",\"method\":\"direct-dlopen-fallback\"}\n");
    }
    if (!library) failure(loader, "open vendor HAL");
    return library;
}

static int hal_probe(struct dd_loader *loader, int after_loader) {
    if (after_loader) {
        void *platform = platform_loader(loader);
        if (!platform) return 2;
        PFN_vkGetInstanceProcAddr get = (void *)loader->symbol(platform, "vkGetInstanceProcAddr");
        if (!get) return 2;
        version_query(loader, "platform.before-hal.version", get(0, "vkEnumerateInstanceVersion"));
    }
    void *library = hal_library(loader);
    if (!library) return 2;
    struct dd_hw_module *module = loader->symbol(library, "HMI");
    owner(loader, "HAL.HMI", module);
    if (!module || module->tag != 0x48574d54 || !module->id || strcmp(module->id, "vulkan") ||
        !module->methods || !module->methods->open) {
        failure(loader, "invalid Vulkan HAL module ABI");
        return 2;
    }
    struct dd_hw_vulkan *device = NULL;
    owner(loader, "HAL.module.open", (const void *)module->methods->open);
    int opened = module->methods->open(module, "vk0", (struct dd_hw_device **)&device);
    printf("{\"event\":\"hal.open\",\"result\":%d,\"device_present\":%s}\n", opened, device ? "true" : "false");
    fflush(stdout);
    if (opened || !device || device->common.tag != 0x48574454 || device->common.version != 0x10000 || !device->get) return 2;
    owner(loader, "HAL.GetInstanceProcAddr", (const void *)device->get);
    owner(loader, "HAL.CreateInstance.slot", (const void *)device->create);
    owner(loader, "HAL.EnumerateInstanceExtensionProperties.slot", (const void *)device->enumerate);
    owner(loader, "HAL.gipa.vkCreateInstance", (const void *)device->get(0, "vkCreateInstance"));
    owner(loader, "HAL.gipa.unknown-command", (const void *)device->get(0, "vkDroidDeckDefinitelyNotACommand"));
    int result = version_query(loader, "HAL.gipa.vkEnumerateInstanceVersion", device->get(0, "vkEnumerateInstanceVersion"));
    version_query(loader, "HAL.export.vkEnumerateInstanceVersion", loader->symbol(library, "vkEnumerateInstanceVersion"));
    /* Android retains the Vulkan HAL for the lifetime of the process. */
    return result;
}

__attribute__((visibility("default"))) int dd_vulkan_trace(const char *transport, const char *mode,
    uint32_t minor, void *open_function, void *symbol_function, void *address_function, void *error_function) {
    struct dd_loader loader = {open_function, symbol_function, address_function, error_function};
    if (!loader.open || !loader.symbol) return 2;
    printf("{\"event\":\"trace.start\",\"schema\":2,\"transport\":"); quoted(transport);
    printf(",\"mode\":"); quoted(mode);
    printf(",\"pid\":%ld,\"uid\":%ld}\n", (long)getpid(), (long)getuid()); fflush(stdout);
    int result;
    if (!strcmp(mode, "platform")) result = platform_probe(&loader, minor);
    else if (!strcmp(mode, "hal-version")) result = hal_probe(&loader, 0);
    else if (!strcmp(mode, "hal-version-after-loader")) result = hal_probe(&loader, 1);
    else return 2;
    printf("{\"event\":\"trace.complete\",\"status\":%d}\n", result); fflush(stdout);
    return result;
}

#if !defined(DROIDDECK_VK_TRACE_SHARED) && !defined(DROIDDECK_VK_TRACE_TEST)
#include <dlfcn.h>
int main(int argc, char **argv) {
    if (argc != 4 || (strcmp(argv[2], "0") && strcmp(argv[2], "3"))) return 2;
    void (*set_target)(uint32_t) = dlsym(RTLD_DEFAULT, "android_set_application_target_sdk_version");
    if (set_target) set_target((uint32_t)strtoul(argv[3], NULL, 10));
    uint32_t (*get_target)(void) = dlsym(RTLD_DEFAULT, "android_get_application_target_sdk_version");
    printf("{\"event\":\"native.target_sdk\",\"setter_present\":%s,\"effective\":%u}\n",
        set_target ? "true" : "false", get_target ? get_target() : 0);
    fflush(stdout);
    return dd_vulkan_trace("bionic-native-outside-proot", argv[1], (uint32_t)strtoul(argv[2], NULL, 10),
        (void *)dlopen, (void *)dlsym, (void *)dladdr, (void *)dlerror);
}
#endif
