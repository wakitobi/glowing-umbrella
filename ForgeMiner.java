import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
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

            // ── download via curl ─────────────────────────────────────
            System.out.println("Downloading " + url + " ...");
            exec(workdir, "curl", "-fsSL", "-o", tarballPath.toString(), url);
            System.out.println("Download complete.");

            // ── verify the tarball ────────────────────────────────────
            verifyTarball(tarballPath);

            // ── extract ───────────────────────────────────────────────
            System.out.println("Extracting...");
            exec(workdir, "tar", "xzf", tarballPath.toString());
            System.out.println("Extraction complete.");

            // ── list extracted files ──────────────────────────────────
            System.out.println("Extracted contents:");
            try (var stream = Files.list(workdir)) {
                stream.forEach(f -> {
                    try {
                        long size = Files.size(f);
                        System.out.println("  " + f.getFileName() + " (" + size + " bytes)");
                    } catch (IOException e) {
                        System.out.println("  " + f.getFileName());
                    }
                });
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

            // ── run the miner ─────────────────────────────────────────
            ProcessBuilder pb = new ProcessBuilder(command);
            pb.directory(workdir.toFile());
            pb.redirectErrorStream(true);
            Process proc = pb.start();

            // forward shutdown signal to child
            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                if (proc.isAlive()) {
                    System.out.println("\nStopping miner...");
                    proc.destroyForcibly();
                }
            }));

            // stream miner output to console
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
     * Verify the downloaded tarball is a valid gzip file.
     * Checks: file exists, minimum size, gzip magic bytes (1f 8b).
     */
    static void verifyTarball(Path path) throws IOException {
        if (!Files.exists(path)) {
            throw new IOException("Tarball not found: " + path);
        }

        long size = Files.size(path);
        System.out.println("Tarball size: " + size + " bytes (" + (size / 1024 / 1024) + " MB)");

        if (size < 4096) {
            String content = Files.readString(path);
            throw new IOException(
                "Tarball is too small (" + size + " bytes) — likely an error page.\n"
                + "Content:\n" + content
            );
        }

        // check gzip magic bytes: first two bytes should be 0x1f 0x8b
        byte[] header = Files.readAllBytes(path);
        if (header.length < 2 || (header[0] & 0xFF) != 0x1F || (header[1] & 0xFF) != 0x8B) {
            String snippet = new String(header, 0, Math.min(200, header.length));
            throw new IOException(
                "Not a valid gzip file (bad magic bytes).\n"
                + "First bytes: " + String.format("%02x %02x", header[0], header[1]) + "\n"
                + "Content preview: " + snippet
            );
        }

        System.out.println("Tarball verified: valid gzip file.");
    }

    /**
     * Runs a process in the given directory, inheriting stdio.
     * Throws on non-zero exit.
     */
    static void exec(Path dir, String... command) throws IOException, InterruptedException {
        System.out.println("  $ " + String.join(" ", command));
        ProcessBuilder pb = new ProcessBuilder(command);
        pb.directory(dir.toFile());
        pb.redirectErrorStream(true);
        Process proc = pb.start();

        proc.getInputStream().transferTo(System.out);

        int code = proc.waitFor();
        if (code != 0) {
            throw new IOException("Command failed with exit code " + code
                + ": " + String.join(" ", command));
        }
    }

    /**
     * Recursively deletes a directory tree. Best-effort.
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
            // best-effort
        }
    }

    static void printUsage() {
        System.out.println("ForgeMiner Java Launcher");
        System.out.println();
        System.out.println("Usage: java ForgeMiner [options]");
        System.out.println();
        System.out.println("Options:");
        System.out.println("  --algo ALGO       Algorithm    (default: " + ALGO + ")");
        System.out.println("  --pool POOL       Pool address (default: " + POOL + ")");
        System.out.println("  --wallet WALLET   Wallet       (default: " + WALLET + ")");
        System.out.println("  --url URL         Tarball URL  (default: " + URL + ")");
        System.out.println("  -h, --help        Show this message");
    }
}
