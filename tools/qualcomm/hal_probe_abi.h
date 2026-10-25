/*
 * Copyright (C) 2008, 2015 The Android Open Source Project
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * http://www.apache.org/licenses/LICENSE-2.0
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
#ifndef DROIDDECK_HAL_PROBE_ABI_H
#define DROIDDECK_HAL_PROBE_ABI_H
#include <stddef.h>
#include <stdint.h>
#include <vulkan/vulkan.h>

struct dd_hw_module;
struct dd_hw_device;
struct dd_hw_methods {
    int (*open)(const struct dd_hw_module *, const char *, struct dd_hw_device **);
};
struct dd_hw_module {
    uint32_t tag;
    uint16_t module_api_version, hal_api_version;
    const char *id, *name, *author;
    struct dd_hw_methods *methods;
    void *dso;
    uint64_t reserved[25];
};
struct dd_hw_device {
    uint32_t tag, version;
    struct dd_hw_module *module;
    uint64_t reserved[12];
    int (*close)(struct dd_hw_device *);
};
struct dd_hw_vulkan {
    struct dd_hw_device common;
    PFN_vkEnumerateInstanceExtensionProperties enumerate;
    PFN_vkCreateInstance create;
    PFN_vkGetInstanceProcAddr get;
};
_Static_assert(sizeof(void *) == 8, "The diagnostic HAL ABI is ARM64 only");
_Static_assert(offsetof(struct dd_hw_module, methods) == 32, "AOSP module ABI");
_Static_assert(sizeof(struct dd_hw_device) == 120, "AOSP device ABI");
_Static_assert(offsetof(struct dd_hw_vulkan, get) == 136, "AOSP Vulkan HAL ABI");
#endif
