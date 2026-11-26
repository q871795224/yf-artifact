/* Opaque declarations from CPython's public configuration and object APIs.
 * No CPython structure layout is used; this translation unit needs only JNI. */
#include <jni.h>
typedef struct PyInitConfig PyInitConfig;
typedef struct _object PyObject;
extern PyInitConfig *PyInitConfig_Create(void);
extern void PyInitConfig_Free(PyInitConfig *);
extern int PyInitConfig_SetStr(PyInitConfig *, const char *, const char *);
extern int PyInitConfig_SetInt(PyInitConfig *, const char *, long long);
extern int PyInitConfig_GetError(PyInitConfig *, const char **);
extern int Py_InitializeFromInitConfig(PyInitConfig *);
extern PyObject *PyImport_ImportModule(const char *);
extern PyObject *PyObject_GetAttrString(PyObject *, const char *);
extern PyObject *PyUnicode_FromString(const char *);
extern PyObject *PyObject_CallOneArg(PyObject *, PyObject *);
extern const char *PyUnicode_AsUTF8(PyObject *);
extern PyObject *PyErr_GetRaisedException(void);
extern PyObject *PyObject_Str(PyObject *);
extern void Py_DecRef(PyObject *);
static PyObject *handler;

static jstring py_error(JNIEnv *env) {
    PyObject *exc = PyErr_GetRaisedException();
    PyObject *msg = exc ? PyObject_Str(exc) : 0;
    jstring text = (*env)->NewStringUTF(env, msg ? PyUnicode_AsUTF8(msg) : "Python initialization failed");
    if (msg) Py_DecRef(msg);
    if (exc) Py_DecRef(exc);
    return text;
}
JNIEXPORT jstring JNICALL Java_org_yfartifact_match_OfflineRules_initialize(JNIEnv *env, jclass cls, jstring home) {
    const char *path = (*env)->GetStringUTFChars(env, home, 0);
    PyInitConfig *cfg = PyInitConfig_Create();
    int status = PyInitConfig_SetStr(cfg, "home", path);
    (*env)->ReleaseStringUTFChars(env, home, path);
    if (!status) status = PyInitConfig_SetInt(cfg, "install_signal_handlers", 0);
    if (!status) status = PyInitConfig_SetInt(cfg, "write_bytecode", 0);
    if (!status) status = Py_InitializeFromInitConfig(cfg);
    if (status < 0) {
        const char *msg = 0;
        PyInitConfig_GetError(cfg, &msg);
        jstring error = (*env)->NewStringUTF(env, msg ? msg : "Python configuration failed");
        PyInitConfig_Free(cfg);
        return error;
    }
    PyInitConfig_Free(cfg);
    PyObject *mod = PyImport_ImportModule("yf_match");
    if (!mod) return py_error(env);
    handler = PyObject_GetAttrString(mod, "request");
    Py_DecRef(mod);
    return handler ? (*env)->NewStringUTF(env, "") : py_error(env);
}
JNIEXPORT jstring JNICALL Java_org_yfartifact_match_OfflineRules_dispatch(JNIEnv *env, jclass cls, jstring input) {
    const char *raw = (*env)->GetStringUTFChars(env, input, 0);
    PyObject *arg = PyUnicode_FromString(raw);
    (*env)->ReleaseStringUTFChars(env, input, raw);
    PyObject *value = arg ? PyObject_CallOneArg(handler, arg) : 0;
    if (arg) Py_DecRef(arg);
    if (!value) {
        jstring message = py_error(env);
        const char *text = (*env)->GetStringUTFChars(env, message, 0);
        (*env)->ThrowNew(env, (*env)->FindClass(env, "java/lang/IllegalStateException"), text);
        (*env)->ReleaseStringUTFChars(env, message, text);
        return 0;
    }
    jstring result = (*env)->NewStringUTF(env, PyUnicode_AsUTF8(value));
    Py_DecRef(value);
    return result;
}
