# Redis local experiment environment

Scope: own isolated runtime under this directory; no global installation, cluster,
external listener, persistent service or existing instance modification.
Existing-binary search under PATH and /opt/homebrew /usr/local /Applications found
no redis-server / redis-cli. Host: macOS arm64.

Official Redis stable header https://download.redis.io/redis-stable/src/version.h
reported REDIS_VERSION=8.10.2 (snapshot stable-version.h).
Version-pinned source: https://download.redis.io/releases/redis-8.10.2.tar.gz
SHA256 b9ffee226b5eecdba98a679260dad764b2a4ebd90dce4ad5ac9e9f3eef9c02b3
matches https://raw.githubusercontent.com/redis/redis-hashes/master/README
(snapshot official-hashes.txt). Source build instructions were read from included
README.md; `make build redis` selects only core structures, with modules skipped.

Actual executed build (completed before author sent subsequent -j1 requirement):
```
make -j4 build redis CC=/opt/homebrew/opt/llvm/bin/clang CXX=/opt/homebrew/opt/llvm/bin/clang++ MALLOC=libc BUILD_TLS=no OPTIMIZATION=-O2
```
No source edits, module dependencies, TLS build or install target. Log: build.log.
Subsequent rebuild command within the new one-thread request:
```
make -j1 build redis CC=/opt/homebrew/opt/llvm/bin/clang CXX=/opt/homebrew/opt/llvm/bin/clang++ MALLOC=libc BUILD_TLS=no OPTIMIZATION=-O2
```
No recompilation is represented as having occurred after the thread requirement.
Actual version/arch/linked libraries/binary hash are in redis-version.txt,
redis-architecture.txt, redis-linked-libraries.txt and actual-sha256.txt.

Runtime: bind127.0.0.1:16379; protected-mode yes; save empty; appendonly no;
maxmemory64mb/noeviction; io-threads1. Complete redis.conf retained.
Python standard-library RESP2 recorder writes base64 request+response bytes,
decoded command/reply, named persistent client, sequence and monotonic timestamp.
Server lifecycle checks its own port, launches a private process group, normally
SHUTDOWN NOSAVE then waits for own PID; fallback signals only own process group.
Official experiment commands will be listed with the frozen author spec once ready.
