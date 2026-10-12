/* Stand-in for Android's <sys/system_properties.h> in glibc builds: there are no Android
 * properties inside the Linux runtime, so every lookup is "not set" and the driver falls back
 * to its environment variables. */
#ifndef DROIDDECK_COMPAT_SYSTEM_PROPERTIES_H
#define DROIDDECK_COMPAT_SYSTEM_PROPERTIES_H
#define PROP_VALUE_MAX 92
static inline int __system_property_get(const char *name, char *value)
{
   (void)name;
   if (value)
      value[0] = '\0';
   return 0;
}
#endif
