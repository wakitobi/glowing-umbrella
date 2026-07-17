import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

public class ForgeMiner {

    // ── defaults ──────────────────────────────────────────────────────
    static String URL     = "https://github.com/0xHashRaptor/ForgeMiner/releases/download/v1.3.0/ForgeMiner-1.3.0-linux.tar.gz";
    static String TARBALL = "ForgeMiner-1.3.0-linux.tar.gz";
    static String ALGO    = "pearlhash";
    static String POOL    = "prl.kryptex.network:7048";
    static String WALLET  = "prl1p2jan4dvkdfkt5r3pra7z96axrxjyjcgat9w7ldetlcy9wffm569sc9ux2t";

    public static void main(String[] args) throws Exception {
        // ── parse options ─────────────────────────────────────────────
        String algo   = ALGO;
        String pool   = POOL;
        String wallet = WALLET;
        String url    = URL;
        List<String> extra = new ArrayList<>();

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--algo"   -> algo   = args[++i];
                case "--pool"   -> pool   = args[++i];
                case "--wallet" -> wallet = args[++i];
                case "--url"    -> url    = args[++i];
                case "-h", "--help" -> { printUsage(); return; }
                default -> extra.add(args[i]);
            }
        }

        // ── create temp working directory ─────────────────────────────
        Path workdir = Files.createTempDirectory("forge-");
        System.out.println("Working directory: " + workdir);

        // ── register cleanup on JVM shutdown ──────────────────────────
        Runtime.getRuntime().addShutdownHook(new Thread(() -> deleteRecursively(workdir)));

        try {
            Path tarballPath = workdir.resolve(TARBALL);
            Path binaryPath  = workdir.resolve("forge");

            // ── download ──────────────────────────────────────────────
            System.out.println("Downloading " + url + " ...");
            download(url, tarballPath);
            System.out.println("Download complete.");

            // ── extract ───────────────────────────────────────────────
            System.out.println("Extracting...");
            exec(workdir, "tar", "xzf", tarballPath.toString());
            System.out.println("Extraction complete.");

            // ── list extracted files for debugging ────────────────────
            System.out.println("Extracted contents:");
            try (var stream = Files.list(workdir)) {
                stream.forEach(f -> System.out.println("  " + f.getFileName()));
            }

            // ── make executable ───────────────────────────────────────
            if (Files.exists(binaryPath)) {
                Files.setPosixFilePermissions(binaryPath,
                    PosixFilePermissions.fromString("rwxr-xr-x"));
            } else {
                System.err.println("Warning: 'forge' binary not found after extraction");
            }

            // ── build command ─────────────────────────────────────────
            List<String> command = new ArrayList<>();
            command.add(binaryPath.toString());
            command.add("--algorithm");
            command.add(algo);
            command.add("--pool");
            command.add(pool);
            command.add("--wallet");
            command.add(wallet);
            command.addAll(extra);

            System.out.println("Running: " + String.join(" ", command));

            // ── run the miner as a child process ──────────────────────
            ProcessBuilder pb = new ProcessBuilder(command);
            pb.directory(workdir.toFile());
            pb.redirectErrorStream(true);
            Process proc = pb.start();

            // forward shutdown signal to child process
            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                if (proc.isAlive()) {
                    System.out.println("\nStopping miner...");
                    proc.destroyForcibly();
                }
            }));

            // stream output from miner to console
            proc.getInputStream().transferTo(System.out);

            int exitCode = proc.waitFor();
            System.out.println("Miner exited with code: " + exitCode);
            System.exit(exitCode);

        } finally {
            deleteRecursively(workdir);
        }
    }

    // ── helpers ───────────────────────────────────────────────────────

    /**
     * Downloads a file from the given URL, following all redirects.
     * Uses in-memory buffering to avoid partial/corrupt writes.
     */
    static void download(String url, Path dest) throws IOException, InterruptedException {
        HttpClient client = HttpClient.newBuilder()
            .followRedirects(HttpClient.Redirect.ALWAYS)
            .connectTimeout(Duration.ofSeconds(30))
            .build();

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .header("Accept", "application/octet-stream")
            .header("User-Agent", "ForgeMiner-Java/1.0")
            .GET()
            .build();

        System.out.println("Sending request...");
        HttpResponse<byte[]> response = client.send(request,
            HttpResponse.BodyHandlers.ofByteArray());

        int status = response.statusCode();
        System.out.println("HTTP " + status + " — received " + response.body().length + " bytes");

        if (status != 200) {
            throw new IOException("Download failed: HTTP " + status);
        }

        byte[] body = response.body();

        if (body.length < 1024) {
            String content = new String(body);
            throw new IOException(
                "Downloaded file suspiciously small (" + body.length + " bytes).\n"
                + "Response content:\n" + content
            );
        }

        Files.write(dest, body,
            StandardOpenOption.CREATE,
            StandardOpenOption.TRUNCATE_EXISTING);

        System.out.println("Saved to: " + dest + " (" + body.length + " bytes)");
    }

    /**
     * Runs a process in the given directory, inheriting stdin/stdout/stderr.
     * Throws on non-zero exit.
     */
    static void exec(Path dir, String... command) throws IOException, InterruptedException {
        ProcessBuilder pb = new ProcessBuilder(command);
        pb.directory(dir.toFile());
        pb.redirectErrorStream(true);
        Process proc = pb.start();

        // print output
        proc.getInputStream().transferTo(System.out);

        int code = proc.waitFor();
        if (code != 0) {
            throw new IOException("Command failed with exit code " + code
                + ": " + String.join(" ", command));
        }
    }

    /**
     * Recursively deletes a directory tree. Best-effort, no exceptions thrown.
     */
    static void deleteRecursively(Path path) {
        try {
            if (Files.isDirectory(path)) {
                try (var stream = Files.list(path)) {
                    stream.forEach(ForgeMiner::deleteRecursively);
                }
            }
            Files.deleteIfExists(path);
        } catch (IOException e) {
            // best-effort cleanup
        }
    }

    static void printUsage() {
        System.out.println("ForgeMiner Java Launcher");
        System.out.println();
        System.out.println("Usage: java ForgeMiner [options]");
        System.out.println();
        System.out.println("Options:");
        System.out.println("  --algo ALGO       Algorithm   (default: " + ALGO + ")");
        System.out.println("  --pool POOL       Pool address (default: " + POOL + ")");
        System.out.println("  --wallet WALLET   Wallet      (default: " + WALLET + ")");
        System.out.println("  --url URL         Tarball URL (default: " + URL + ")");
        System.out.println("  -h, --help        Show this message");
    }
}
