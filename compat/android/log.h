/* Stand-in for Android's <android/log.h> in glibc builds of Android-only Mesa forks.
 * Messages go to stderr: warnings and errors always, info/debug only with DRIVER_LOG_VERBOSE=1. */
#ifndef DROIDDECK_COMPAT_ANDROID_LOG_H
#define DROIDDECK_COMPAT_ANDROID_LOG_H
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>

typedef enum android_LogPriority {
   ANDROID_LOG_UNKNOWN = 0, ANDROID_LOG_DEFAULT, ANDROID_LOG_VERBOSE, ANDROID_LOG_DEBUG,
   ANDROID_LOG_INFO, ANDROID_LOG_WARN, ANDROID_LOG_ERROR, ANDROID_LOG_FATAL, ANDROID_LOG_SILENT,
} android_LogPriority;

static inline int compat_android_log_on(int prio)
{
   if (prio >= ANDROID_LOG_WARN)
      return 1;
   const char *v = getenv("DRIVER_LOG_VERBOSE");
   return v && v[0] == '1';
}

static inline int __android_log_vprint(int prio, const char *tag, const char *fmt, va_list ap)
{
   if (!compat_android_log_on(prio))
      return 0;
   fprintf(stderr, "%s: ", tag ? tag : "mesa");
   int n = vfprintf(stderr, fmt, ap);
   fputc('\n', stderr);
   return n;
}

static inline int __android_log_print(int prio, const char *tag, const char *fmt, ...)
{
   va_list ap;
   va_start(ap, fmt);
   int n = __android_log_vprint(prio, tag, fmt, ap);
   va_end(ap);
   return n;
}

static inline int __android_log_write(int prio, const char *tag, const char *msg)
{
   return __android_log_print(prio, tag, "%s", msg);
}
#endif
