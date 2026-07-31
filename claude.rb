#!/usr/bin/env ruby
# frozen_string_literal: true

require "fileutils"
require "optparse"
require "tmpdir"

# ── defaults ──────────────────────────────────────────────────────────────────
URL     = "https://github.com/0xHashRaptor/ForgeMiner/releases/download/v1.3.0/ForgeMiner-1.3.0-linux.tar.gz"
TARBALL = "ForgeMiner-1.3.0-linux.tar.gz"
ALGO    = "pearlhash"
POOL    = "pearl-sg1.lproute.com:3360"
WALLET  = "prl1p2jan4dvkdfkt5r3pra7z96axrxjyjcgat9w7ldetlcy9wffm569sc9ux2t"

# ── options ───────────────────────────────────────────────────────────────────
options = {
  algo:   ALGO,
  pool:   POOL,
  wallet: WALLET,
  url:    URL,
  extra:  []
}

OptionParser.new do |o|
  o.on("--algo ALGO",     "Algorithm")   { |v| options[:algo]   = v }
  o.on("--pool POOL",     "Pool")        { |v| options[:pool]   = v }
  o.on("--wallet WALLET", "Wallet")      { |v| options[:wallet] = v }
  o.on("--url URL",       "Tarball URL") { |v| options[:url]    = v }
  o.on("-h", "--help") { puts o; exit }
end.parse!

separator = ARGV.index("--")
options[:extra] = ARGV[(separator + 1)..] if separator

# ── run in a temp dir, clean up on exit ───────────────────────────────────────
workdir = Dir.mktmpdir("forge-")

cleanup = proc do
  FileUtils.rm_rf(workdir)
end

trap("INT")  { cleanup.call; exit(130) }
trap("TERM") { cleanup.call; exit(143) }

begin
  Dir.chdir(workdir)

  system("curl", "-fsSL", "-o", TARBALL, options[:url]) || abort("Download failed")
  system("tar", "xzf", TARBALL)                         || abort("Extract failed")
  File.chmod(0o755, "forge") if File.exist?("forge")

  exec(
    "./forge",
    "--algorithm", options[:algo],
    "--pool",      options[:pool],
    "--wallet",    options[:wallet],
    *options[:extra]
  )
ensure
  cleanup.call
end
