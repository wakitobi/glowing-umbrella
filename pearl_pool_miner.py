#!/usr/bin/env python3
"""
Pearl GPU Pool Miner for T4 (sm75)
===================================
Full GPU-accelerated Pearl NoisyGEMM PoW miner for NVIDIA T4.

Uses:
  - PyTorch GPU for matmul (fp16 tensor cores, 65 TFLOPS on T4)
  - pearl_mining Rust library for Merkle trees + PlainProof construction
  - LuckyPool Stratum-like protocol for pool mining

Architecture:
  1. Connect to pool, receive job (header, target)
  2. Generate random signal matrices A, B on GPU
  3. Build Merkle trees (CPU, pearl_mining)
  4. Derive commitment hashes → noise seeds
  5. Generate noise matrices, add to A/B
  6. GPU: tiled matmul with PoW checking per 16x16 tile
  7. On PoW hit: build PlainProof, gzip, hex-encode, submit

Requirements:
  pip install torch blake3
  # Build pearl_mining from repo:
  cd pearl/py-pearl-mining && pip install -e .

Usage:
  python pearl_pool_miner.py [--pool HOST:PORT] [--wallet ADDR] [--worker NAME]
"""

import argparse
import gzip
import json
import math
import os
import socket
import struct
import sys
import time
import traceback
from dataclasses import dataclass
from math import ceil

import numpy as np
import torch

# blake3 — try the C extension first, fall back to hashlib
try:
    from blake3 import blake3
except ImportError:
    import hashlib
    class blake3:
        digest_size = 32
        def __init__(self, data=b"", key=None):
            if key:
                self._h = hashlib.blake3(data, key=key)  # Python 3.13+ or blake3 lib
            else:
                self._h = hashlib.blake3(data)
        def digest(self):
            return self._h.digest()
        def update(self, data):
            self._h.update(data)
            return self

# pearl_mining — Rust library for Merkle trees and proof construction
try:
    from pearl_mining import (
        MERKLE_LEAF_SIZE,
        MatrixMerkleProof,
        MerkleTree,
        MiningConfiguration,
        MMAType,
        PeriodicPattern,
        PlainProof,
        pad_to_chunk_boundary,
    )
    HAS_PEARL_MINING = True
except ImportError:
    HAS_PEARL_MINING = False
    print("[WARN] pearl_mining not found — will mine but cannot submit proofs")
    print("       Build from: cd pearl/py-pearl-mining && pip install -e .")

# ═══════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════

HASH_TILE_H = 16
HASH_TILE_W = 16
NOISE_RANK = 128
NOISE_RANGE = 128
DATA_RANGE = 256 - NOISE_RANGE  # 128
DATA_MIN = -(DATA_RANGE // 2)   # -64
DATA_MAX = DATA_MIN + DATA_RANGE - 1  # 63
TRANSCRIPT_SIZE_U32 = 16
HASH_ACCUMULATE_ROTATION = 13

# V3 salting constants
SEED_SALT_A = blake3(b"pearl/cert-v3/noise-seed/A").digest()
SEED_SALT_B = blake3(b"pearl/cert-v3/noise-seed/B").digest()
BIND_PAD = b"\x00" * 28

# Default dims
DEFAULT_M = 4096
DEFAULT_N = 4096
DEFAULT_K = 4096


# ═══════════════════════════════════════════════════════════════════════
# Pool Protocol Client
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class PoolJob:
    job_id: str
    header: bytes        # incomplete header bytes
    target: int          # 256-bit target
    diff: int
    cert_version: int
    height: int


class PoolClient:
    """LuckyPool Stratum-like JSON-RPC client for Pearl."""

    def __init__(self, host: str, port: int, wallet: str, worker: str = "t4"):
        self.host = host
        self.port = port
        self.wallet = wallet
        self.worker = worker
        self.sock = None
        self.buf = b""
        self.req_id = 0
        self.current_job: PoolJob | None = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(30)
        self.sock.connect((self.host, self.port))
        print(f"[POOL] Connected to {self.host}:{self.port}")
        self._authorize()

    def _send(self, method: str, params: dict) -> dict | None:
        self.req_id += 1
        req = {"jsonrpc": "2.0", "method": method, "id": self.req_id, "params": params}
        line = json.dumps(req) + "\n"
        self.sock.sendall(line.encode())
        return self._recv_response(self.req_id)

    def _recv_response(self, expected_id: int, timeout: float = 15.0) -> dict | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            # Check buffer for complete lines
            while b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                msg = json.loads(line)
                # Pool push notification
                if msg.get("method") == "mining.notify":
                    self._handle_notify(msg.get("params", {}))
                    continue
                if msg.get("id") == expected_id:
                    return msg
            # Read more
            try:
                self.sock.settimeout(max(0.1, deadline - time.time()))
                data = self.sock.recv(8192)
                if not data:
                    raise ConnectionError("Pool disconnected")
                self.buf += data
            except socket.timeout:
                continue
        return None

    def _authorize(self):
        resp = self._send("mining.authorize", {"wallet": self.wallet, "worker": self.worker})
        if resp and resp.get("result"):
            print(f"[POOL] Authorized as {self.worker}")
        else:
            raise RuntimeError(f"Authorization failed: {resp}")
        # Pool should push mining.notify after auth — wait for it
        self._wait_for_job(timeout=30)

    def _handle_notify(self, params: dict):
        try:
            header_hex = params.get("header", "")
            target_hex = params.get("target", "0")
            self.current_job = PoolJob(
                job_id=params.get("job_id", ""),
                header=bytes.fromhex(header_hex),
                target=int(target_hex, 16),
                diff=params.get("diff", 0),
                cert_version=params.get("cert_version", 3),
                height=params.get("height", 0),
            )
            print(f"[POOL] New job: height={self.current_job.height} "
                  f"diff={self.current_job.diff} job_id={self.current_job.job_id[:16]}...")
        except Exception as e:
            print(f"[POOL] Error parsing notify: {e}")

    def _wait_for_job(self, timeout: float = 30.0):
        deadline = time.time() + timeout
        while self.current_job is None and time.time() < deadline:
            # Check buffer first (data may already be buffered from prior recv)
            while b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                try:
                    msg = json.loads(line)
                    if msg.get("method") == "mining.notify":
                        self._handle_notify(msg.get("params", {}))
                except json.JSONDecodeError:
                    pass
            if self.current_job is not None:
                break
            # Read more from socket
            try:
                self.sock.settimeout(max(0.1, deadline - time.time()))
                data = self.sock.recv(8192)
                if not data:
                    raise ConnectionError("Pool disconnected while waiting for job")
                self.buf += data
            except socket.timeout:
                continue
        if self.current_job is None:
            raise RuntimeError("No mining job received from pool")

    def submit(self, proof_bytes: bytes, job_id: str) -> bool:
        """Submit gzipped proof as hex to pool."""
        compressed = gzip.compress(proof_bytes, compresslevel=1)
        nonce_hex = compressed.hex()
        resp = self._send("mining.submit", {"job_id": job_id, "nonce": nonce_hex})
        if resp:
            if resp.get("error"):
                print(f"[POOL] Submit rejected: {resp['error']}")
                return False
            print(f"[POOL] Share accepted!")
            return True
        print("[POOL] Submit timed out")
        return False

    def poll_jobs(self):
        """Non-blocking check for new jobs."""
        try:
            self.sock.settimeout(0.001)
            data = self.sock.recv(8192)
            if data:
                self.buf += data
                while b"\n" in self.buf:
                    line, self.buf = self.buf.split(b"\n", 1)
                    msg = json.loads(line)
                    if msg.get("method") == "mining.notify":
                        self._handle_notify(msg.get("params", {}))
        except (socket.timeout, BlockingIOError):
            pass

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None


# ═══════════════════════════════════════════════════════════════════════
# Noise Generation (pure Python, matching Rust/reference exactly)
# ═══════════════════════════════════════════════════════════════════════

def np_mul_hi_u32(a: np.uint32, b: np.uint32) -> np.uint32:
    prod64 = a.astype(np.uint64) * b.astype(np.uint64)
    return (prod64 >> np.uint64(32)).astype(np.uint32)


def _get_random_hash(index: int, seed: bytes, key: bytes, prepend_index: int) -> bytes:
    message_prepend = np.zeros(8, dtype=np.int32)
    message_prepend[prepend_index] = 1 + index
    message_bytes = message_prepend.tobytes() + seed
    return blake3(message_bytes, key=key).digest()


def generate_uniform_random_matrix(seed: bytes, key: bytes, rows: int, rank: int) -> torch.Tensor:
    """Generate uniform random noise matrix (rows x rank) as int8."""
    cols = rank
    draws = ceil(rows * cols / 32)
    random_bytes = b"".join(_get_random_hash(i, seed, key, 0) for i in range(draws))
    random_tensor = torch.frombuffer(bytearray(random_bytes), dtype=torch.uint8)[:rows * cols]
    range_mask = (NOISE_RANGE // 2) - 1  # 63
    zero_point = NOISE_RANGE // 4        # 32
    return ((random_tensor & range_mask) - zero_point).to(torch.int8).view(rows, cols)


def generate_permutation_matrix(seed: bytes, key: bytes, rows: int, cols: int,
                                 rank: int, assign_columns: bool) -> torch.Tensor:
    """Generate permutation noise matrix as int8."""
    noise_matrix = torch.zeros(rows, cols, dtype=torch.int8)
    required_lines = cols if assign_columns else rows
    rank_mask = rank - 1
    bytes_per_line = 4
    draws = ceil(required_lines * bytes_per_line / 32)

    for i in range(draws):
        random_hash = _get_random_hash(i, seed, key, 1)
        random_uint32_array = np.frombuffer(random_hash, dtype=np.uint32)
        for k_idx in range(32 // bytes_per_line):
            assignment_index = i * 32 // bytes_per_line + k_idx
            if assignment_index >= required_lines:
                break
            random_uint32 = random_uint32_array[k_idx]
            first_idx = int(random_uint32 & rank_mask)
            second_idx = int(first_idx ^ (1 + np_mul_hi_u32(np.uint32(rank - 1), random_uint32)))
            permutation = torch.zeros(rank, dtype=torch.int8)
            permutation[first_idx] = 1
            permutation[second_idx] = -1
            if assign_columns:
                noise_matrix[:, assignment_index] = permutation
            else:
                noise_matrix[assignment_index, :] = permutation

    return noise_matrix


def generate_noise_matrices(key_A: bytes, key_B: bytes, m: int, k: int, n: int, rank: int):
    """Generate all 4 noise matrices E_AL, E_AR, E_BL, E_BR."""
    seed_A = (b"A_tensor" + b"\x00" * 24)
    seed_B = (b"B_tensor" + b"\x00" * 24)

    E_AL = generate_uniform_random_matrix(seed_A, key_A, m, rank)       # m x r
    E_AR = generate_permutation_matrix(seed_A, key_A, rank, k, rank, assign_columns=True)  # r x k
    E_BL = generate_permutation_matrix(seed_B, key_B, k, rank, rank, assign_columns=False) # k x r
    E_BR = generate_uniform_random_matrix(seed_B, key_B, n, rank)       # n x r → need .T → r x n

    return E_AL, E_AR, E_BL, E_BR.T.contiguous()


# ═══════════════════════════════════════════════════════════════════════
# Commitment Hash (matches reference exactly)
# ═══════════════════════════════════════════════════════════════════════

def bind_root(merkle_root: bytes, dim: int, salt: bytes) -> bytes:
    return blake3(merkle_root + dim.to_bytes(4, "little") + BIND_PAD, key=salt).digest()


def compute_commitment_hash(A_root: bytes, B_root: bytes, key: bytes,
                             m: int, n: int, cert_version: int):
    """Compute CommitmentHash (noise_seed_A, noise_seed_B)."""
    # V3 salted derivation
    if cert_version >= 3:
        A_root = bind_root(A_root, m, SEED_SALT_A)
        B_root = bind_root(B_root, n, SEED_SALT_B)
    noise_seed_B = blake3(key + B_root).digest()
    noise_seed_A = blake3(noise_seed_B + A_root).digest()
    return noise_seed_A, noise_seed_B


# ═══════════════════════════════════════════════════════════════════════
# Merkle Tree wrapper
# ═══════════════════════════════════════════════════════════════════════

def pad_tensor(tensor: torch.Tensor) -> bytes:
    """Convert tensor to bytes, padded to BLAKE3 chunk boundary."""
    raw = tensor.flatten().detach().cpu().numpy().tobytes()
    return pad_to_chunk_boundary(raw)


def build_merkle_tree(tensor: torch.Tensor, key: bytes):
    """Build a MerkleTree from a 2D int8 tensor."""
    return MerkleTree(data=pad_tensor(tensor), key=key)


def leaf_indices_from_rows(row_indices: list, shape: tuple) -> list:
    """Compute Merkle leaf indices from row indices."""
    return MerkleTree.compute_leaf_indices_from_rows(row_indices, shape)


# ═══════════════════════════════════════════════════════════════════════
# Mining Configuration
# ═══════════════════════════════════════════════════════════════════════

def make_mining_config(k: int, row_indices: list, col_indices: list) -> "MiningConfiguration":
    """Build MiningConfiguration from row/col indices of the winning tile."""
    row_offset = min(row_indices)
    col_offset = min(col_indices)
    rows_pattern = PeriodicPattern.from_list([i - row_offset for i in row_indices])
    cols_pattern = PeriodicPattern.from_list([i - col_offset for i in col_indices])
    return MiningConfiguration(
        common_dim=k,
        rank=NOISE_RANK,
        mma_type=MMAType.Int7xInt7ToInt32,
        rows_pattern=rows_pattern,
        cols_pattern=cols_pattern,
        moe=None,
    )


# ═══════════════════════════════════════════════════════════════════════
# GPU Mining Engine
# ═══════════════════════════════════════════════════════════════════════

def rotl32(x, n):
    """Rotate left 32-bit."""
    x = x & 0xFFFFFFFF
    return ((x << n) | (x >> (32 - n))) & 0xFFFFFFFF


class GPUMiner:
    """GPU-accelerated Pearl NoisyGEMM miner for T4."""

    def __init__(self, m=DEFAULT_M, n=DEFAULT_N, k=DEFAULT_K, device="cuda"):
        self.m = m
        self.n = n
        self.k = k
        self.device = device
        self.total_hashes = 0
        self.total_shares = 0
        self.start_time = time.time()

        # Check GPU
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA not available")
        gpu = torch.cuda.get_device_properties(0)
        total_mem = getattr(gpu, 'total_memory', None) or getattr(gpu, 'total_mem', 0)
        print(f"[GPU] {gpu.name}, {total_mem / 1e9:.1f} GB, sm{gpu.major}{gpu.minor}")

        # Check if we should use int8 (sm80+) or fp16 path
        self.use_int8 = gpu.major >= 8
        if self.use_int8:
            print("[GPU] Using int8 tensor cores (sm80+)")
        else:
            print("[GPU] Using fp16 tensor cores (T4/sm75)")

    def mine_once(self, header: bytes, target: int, cert_version: int):
        """
        One mining attempt: generate matrices, compute GEMM, check PoW.
        Returns (found, row_indices, col_indices, A_cpu, Bt_cpu, key, config)
        or (False, ...) if no solution found.
        """
        m, n, k = self.m, self.n, self.k

        # 1. Generate random signal matrices A (m×k), B (k×n) in [-64, 63]
        A = torch.randint(DATA_MIN, DATA_MAX + 1, (m, k), dtype=torch.int8, device="cpu")
        B = torch.randint(DATA_MIN, DATA_MAX + 1, (k, n), dtype=torch.int8, device="cpu")

        # Standard config: 16 consecutive rows/cols starting at 0 (periodic)
        default_rows = list(range(HASH_TILE_H))
        default_cols = list(range(HASH_TILE_W))
        config = make_mining_config(k, default_rows, default_cols)

        # 2. Compute commitment key
        config_bytes = config.to_bytes()
        key = blake3(header + config_bytes).digest()

        # 3. Build Merkle trees for A and B^T (CPU)
        A_tree = build_merkle_tree(A, key)
        B_t = B.T.contiguous()
        B_tree = build_merkle_tree(B_t, key)

        # 4. Compute commitment hashes (noise seeds)
        noise_seed_A, noise_seed_B = compute_commitment_hash(
            A_tree.root, B_tree.root, key, m, n, cert_version
        )

        # 5. Generate noise matrices (CPU)
        E_AL, E_AR, E_BL, E_BR = generate_noise_matrices(
            noise_seed_A, noise_seed_B, m, k, n, NOISE_RANK
        )

        # 6. Add noise and move to GPU
        E_A = torch.matmul(E_AL.to(torch.int32), E_AR.to(torch.int32)).clamp(-128, 127).to(torch.int8)
        A_noised = (A.to(torch.int16) + E_A.to(torch.int16)).clamp(-128, 127).to(torch.int8)

        E_B = torch.matmul(E_BL.to(torch.int32), E_BR.to(torch.int32)).clamp(-128, 127).to(torch.int8)
        B_noised = (B.to(torch.int16) + E_B.to(torch.int16)).clamp(-128, 127).to(torch.int8)

        # 7. GPU: full matmul + vectorized PoW check
        pow_key = noise_seed_A
        found, win_row, win_col = self._gpu_matmul_pow(
            A_noised, B_noised, k, pow_key, target
        )

        if found:
            row_indices = list(range(win_row, win_row + HASH_TILE_H))
            col_indices = list(range(win_col, win_col + HASH_TILE_W))
            return True, row_indices, col_indices, A, B_t, key, config

        return False, None, None, None, None, None, None

    def _gpu_matmul_pow(self, A_noised, B_noised, k, pow_key, target):
        """
        Full GPU matmul with vectorized transcript accumulation.
        Does ONE big matmul on GPU, then vectorized XOR-reduce per tile.
        Only blake3 PoW check runs on CPU (unavoidable).
        """
        m, _ = A_noised.shape
        _, n = B_noised.shape
        dev = self.device

        num_k_tiles = k // NOISE_RANK  # 4096/128 = 32

        # Number of 16x16 hash tiles in the output
        th = m // HASH_TILE_H   # 4096/16 = 256
        tw = n // HASH_TILE_W   # 4096/16 = 256
        num_tiles = th * tw     # 65536

        # Transcript state: (num_tiles, 16) as uint32 on GPU
        transcripts = torch.zeros((num_tiles, TRANSCRIPT_SIZE_U32), dtype=torch.int64, device=dev)

        # Process k-dimension in chunks of NOISE_RANK
        # Each chunk: partial matmul → accumulate into running C → XOR-reduce hash tiles
        C_accum = torch.zeros((m, n), dtype=torch.int32, device=dev)

        for kk in range(num_k_tiles):
            p = kk * NOISE_RANK

            A_tile = A_noised[:, p:p+NOISE_RANK]
            B_tile = B_noised[p:p+NOISE_RANK, :]

            if self.use_int8:
                A_gpu = A_tile.to(dev)
                B_gpu = B_tile.to(dev)
                C_part = torch._int_mm(A_gpu, B_gpu)
            else:
                A_gpu = A_tile.to(torch.float16).to(dev)
                B_gpu = B_tile.to(torch.float16).to(dev)
                C_part = torch.matmul(A_gpu, B_gpu).to(torch.int32)

            C_accum += C_part

            # Vectorized XOR-reduce each 16x16 tile
            # Reshape C_accum → (th, 16, tw, 16) → (th*tw, 256) → XOR reduce
            C_tiles = C_accum.view(th, HASH_TILE_H, tw, HASH_TILE_W)
            C_tiles = C_tiles.permute(0, 2, 1, 3).contiguous()  # (th, tw, 16, 16)
            C_tiles = C_tiles.view(num_tiles, HASH_TILE_H * HASH_TILE_W)  # (65536, 256)

            # XOR-reduce all 256 int32s in each tile to a single uint32
            # Use bitwise_xor reduction via torch
            xor_reduced = C_tiles[:, 0]
            for j in range(1, HASH_TILE_H * HASH_TILE_W):
                xor_reduced = xor_reduced ^ C_tiles[:, j]
            # xor_reduced: (num_tiles,) int32

            # Accumulate into transcript: rotl13(old) ^ xor_val
            idx = kk % TRANSCRIPT_SIZE_U32
            old = transcripts[:, idx]
            # rotl32 vectorized: ((x << 13) | (x >> 19)) & 0xFFFFFFFF
            mask = 0xFFFFFFFF
            rotated = ((old << HASH_ACCUMULATE_ROTATION) | (old >> (32 - HASH_ACCUMULATE_ROTATION))) & mask
            transcripts[:, idx] = rotated ^ (xor_reduced.to(torch.int64) & mask)

        # PoW check: move transcripts to CPU, blake3 each one
        transcripts_cpu = transcripts.cpu().numpy().astype(np.uint32)  # (num_tiles, 16)

        for tile_idx in range(num_tiles):
            transcript_bytes = transcripts_cpu[tile_idx].tobytes()  # 64 bytes, already uint32 LE
            hash_result = blake3(transcript_bytes, key=pow_key).digest()

            self.total_hashes += 1

            # Compare as little-endian integer (matches reference implementation)
            hash_int = int.from_bytes(hash_result, "little")
            if hash_int <= target:
                ti = tile_idx // tw
                tj = tile_idx % tw
                win_row = ti * HASH_TILE_H
                win_col = tj * HASH_TILE_W
                return True, win_row, win_col

        return False, -1, -1

    def build_and_submit_proof(self, pool: PoolClient, job: PoolJob,
                                row_indices, col_indices, A, B_t, key, config):
        """Build PlainProof from matrices and submit to pool."""
        if not HAS_PEARL_MINING:
            print("[WARN] Cannot submit — pearl_mining not installed")
            return False

        m, k_dim = A.shape
        n, k2 = B_t.shape
        assert k_dim == k2

        # Build Merkle trees
        A_tree = build_merkle_tree(A, key)
        B_tree = build_merkle_tree(B_t, key)

        # Build Merkle proofs for the winning tile rows/cols
        a_leaf_indices = leaf_indices_from_rows(row_indices, A.shape)
        a_proof = A_tree.get_multileaf_proof(a_leaf_indices)
        a_merkle_proof = MatrixMerkleProof(proof=a_proof, row_indices=row_indices)

        b_leaf_indices = leaf_indices_from_rows(col_indices, B_t.shape)
        b_proof = B_tree.get_multileaf_proof(b_leaf_indices)
        b_merkle_proof = MatrixMerkleProof(proof=b_proof, row_indices=col_indices)

        # Create PlainProof
        plain_proof = PlainProof(
            m=m,
            n=n,
            k=k_dim,
            noise_rank=NOISE_RANK,
            a_merkle_proof=a_merkle_proof,
            bt_merkle_proof=b_merkle_proof,
            moe=None,
        )

        # Serialize: PlainProof → base64 → decode to bytes (bincode format)
        proof_b64 = plain_proof.to_base64()
        import base64
        proof_bytes = base64.b64decode(proof_b64)

        print(f"[PROOF] Built PlainProof: m={m} n={n} k={k_dim} "
              f"rows={row_indices[0]}..{row_indices[-1]} "
              f"cols={col_indices[0]}..{col_indices[-1]} "
              f"size={len(proof_bytes)} bytes")

        # Submit to pool
        return pool.submit(proof_bytes, job.job_id)


# ═══════════════════════════════════════════════════════════════════════
# Main Mining Loop
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Pearl GPU Pool Miner (T4)")
    parser.add_argument("--pool", default="pearl-us-ord.lproute.com:3360",
                       help="Pool host:port")
    parser.add_argument("--wallet",
                       default="prl1p2jan4dvkdfkt5r3pra7z96axrxjyjcgat9w7ldetlcy9wffm569sc9ux2t",
                       help="Pearl wallet address")
    parser.add_argument("--worker", default="t4", help="Worker name")
    parser.add_argument("--m", type=int, default=DEFAULT_M, help="Matrix M dimension")
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="Matrix N dimension")
    parser.add_argument("--k", type=int, default=DEFAULT_K, help="Matrix K dimension")
    args = parser.parse_args()

    host, port = args.pool.rsplit(":", 1)
    port = int(port)

    print("=" * 60)
    print("Pearl GPU Pool Miner — T4 Edition")
    print("=" * 60)

    # Initialize GPU miner
    miner = GPUMiner(m=args.m, n=args.n, k=args.k)

    # Connect to pool
    pool = PoolClient(host, port, args.wallet, args.worker)
    pool.connect()

    attempt = 0
    shares = 0

    try:
        while True:
            job = pool.current_job
            if job is None:
                pool._wait_for_job()
                continue

            attempt += 1
            job_snapshot = pool.current_job  # snapshot before mining

            t0 = time.time()
            found, row_idx, col_idx, A, B_t, key, config = miner.mine_once(
                job.header, job.target, job.cert_version
            )
            elapsed = time.time() - t0

            # Check if job changed during mining
            if pool.current_job and pool.current_job.job_id != job_snapshot.job_id:
                print(f"[MINE] Job changed during mining, discarding attempt")
                continue

            hps = miner.total_hashes / (time.time() - miner.start_time) if time.time() > miner.start_time else 0

            if found:
                print(f"[MINE] *** SHARE FOUND *** attempt={attempt} "
                      f"elapsed={elapsed:.1f}s hashes={miner.total_hashes} H/s={hps:.0f}")
                if miner.build_and_submit_proof(pool, job_snapshot, row_idx, col_idx, A, B_t, key, config):
                    shares += 1
                    print(f"[MINE] Total shares: {shares}")
            else:
                if attempt % 10 == 0:
                    print(f"[MINE] attempt={attempt} elapsed={elapsed:.1f}s "
                          f"total_hashes={miner.total_hashes} H/s={hps:.0f} shares={shares}")

            # Poll for new jobs
            pool.poll_jobs()

    except KeyboardInterrupt:
        print(f"\n[EXIT] {shares} shares in {attempt} attempts")
    finally:
        pool.close()


if __name__ == "__main__":
    main()
