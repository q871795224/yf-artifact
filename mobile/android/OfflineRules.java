package org.yfartifact.match;

import java.io.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicReference;
import java.util.zip.*;
import org.json.JSONObject;

/** One worker owns the interpreter. Godot polls without blocking its render thread. */
public final class OfflineRules {
    private static final ExecutorService worker = Executors.newSingleThreadExecutor();
    private static final AtomicReference<String> reply = new AtomicReference<>();
    private static boolean pending, initialized;
    private static native String initialize(String home);
    private static native String dispatch(String json);

    public static synchronized boolean submit(String apk, String data, String json) {
        if (pending) return false;
        pending = true;
        worker.execute(() -> {
            try {
                if (!initialized) {
                    File home = install(apk, data);
                    System.loadLibrary("python3.14");
                    System.loadLibrary("yfrules");
                    String error = initialize(home.getAbsolutePath());
                    if (!error.isEmpty()) throw new IOException(error);
                    initialized = true;
                }
                reply.set(dispatch(json));
            } catch (Throwable error) {
                reply.set("{\"error\":" + JSONObject.quote(error.toString()) + "}");
            }
        });
        return true;
    }
    public static synchronized String poll() {
        String result = reply.getAndSet(null);
        if (result == null) return "";
        pending = false;
        return result;
    }

    private static File install(String apkPath, String data) throws IOException {
        try (ZipFile apk = new ZipFile(apkPath)) {
            ZipEntry payload = apk.getEntry("assets/yf_runtime-" + android.os.Build.SUPPORTED_ABIS[0] + ".zip");
            File home = new File(data, "rules-" + Long.toHexString(payload.getCrc()));
            File ready = new File(home, ".ready");
            if (ready.isFile()) return home;
            if (!home.isDirectory() && !home.mkdirs()) throw new IOException("无法创建规则目录");
            String prefix = home.getCanonicalPath() + File.separator;
            try (ZipInputStream stream = new ZipInputStream(apk.getInputStream(payload))) {
                byte[] buf = new byte[65536];
                ZipEntry entry;
                while ((entry = stream.getNextEntry()) != null) {
                    File out = new File(home, entry.getName());
                    if (!out.getCanonicalPath().startsWith(prefix)) throw new IOException("无效的资源路径");
                    File dir = out.getParentFile();
                    if (!dir.isDirectory() && !dir.mkdirs()) throw new IOException("无法创建资源目录");
                    try (FileOutputStream writer = new FileOutputStream(out)) {
                        int count;
                        while ((count = stream.read(buf)) != -1) writer.write(buf, 0, count);
                    }
                }
            }
            if (!ready.createNewFile()) throw new IOException("规则初始化失败");
            return home;
        }
    }
}
