#include "rio.h"

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

typedef struct {
    const char *pieces[8];
    size_t piece_count;
    size_t index;
    int inject_eintr_at;
    int calls;
    char captured[128];
    size_t captured_used;
    size_t maximum_write;
} scripted_io;

static volatile sig_atomic_t sigchld_seen = 0;
static volatile sig_atomic_t timed_out = 0;

static void mark_sigchld(int signal_number) {
    (void)signal_number;
    sigchld_seen = 1; /* No printf, malloc, or waitpid in this handler. */
}

static void mark_timeout(int signal_number) {
    (void)signal_number;
    timed_out = 1;
}

static ssize_t scripted_read(int fd, void *buffer, size_t count, void *context) {
    scripted_io *script = context;
    (void)fd;
    script->calls++;
    if (script->calls == script->inject_eintr_at) {
        errno = EINTR;
        return -1;
    }
    if (script->index == script->piece_count) {
        return 0;
    }
    size_t length = strlen(script->pieces[script->index]);
    if (length > count) {
        length = count;
    }
    memcpy(buffer, script->pieces[script->index], length);
    script->index++;
    return (ssize_t)length;
}

static ssize_t scripted_write(int fd, void *buffer, size_t count, void *context) {
    scripted_io *script = context;
    (void)fd;
    size_t length = count < script->maximum_write ? count : script->maximum_write;
    script->calls++;
    if (script->calls == script->inject_eintr_at) {
        errno = EINTR;
        return -1;
    }
    if (script->captured_used + length > sizeof(script->captured)) {
        errno = ENOSPC;
        return -1;
    }
    memcpy(script->captured + script->captured_used, buffer, length);
    script->captured_used += length;
    return (ssize_t)length;
}

static int require_true(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "self-test failed: %s\n", message);
        return 0;
    }
    return 1;
}

static int test_injected_io(void) {
    char bytes[8] = {0};
    scripted_io input = {.pieces = {"ab", "cde"}, .piece_count = 2, .inject_eintr_at = 2};
    rio_hooks input_hooks = {.read_fn = scripted_read, .context = &input};
    if (!require_true(rio_readn(-1, bytes, 5, &input_hooks) == 5, "readn total")) return 0;
    if (!require_true(memcmp(bytes, "abcde", 5) == 0, "readn order")) return 0;
    if (!require_true(rio_readn(-1, bytes, 0, &input_hooks) == 0, "readn count=0")) return 0;

    scripted_io output = {.inject_eintr_at = 2, .maximum_write = 2};
    rio_hooks output_hooks = {.write_fn = scripted_write, .context = &output};
    if (!require_true(rio_writen(-1, "ABCDE", 5, &output_hooks) == 0, "writen total")) return 0;
    if (!require_true(output.captured_used == 5 && memcmp(output.captured, "ABCDE", 5) == 0,
                      "writen order")) return 0;

    scripted_io lines = {.pieces = {"one\nvery", "long\nend\n"}, .piece_count = 2};
    rio_hooks line_hooks = {.read_fn = scripted_read, .context = &lines};
    rio_reader reader;
    rio_reader_init(&reader, -1, &line_hooks);
    char line[5];
    if (!require_true(rio_readline(&reader, line, sizeof(line)) == 4 && strcmp(line, "one\n") == 0,
                      "first line")) return 0;
    errno = 0;
    if (!require_true(rio_readline(&reader, line, sizeof(line)) == -1 && errno == EOVERFLOW,
                      "overlong line discarded")) return 0;
    if (!require_true(rio_readline(&reader, line, sizeof(line)) == 4 && strcmp(line, "end\n") == 0,
                      "next line remains aligned")) return 0;
    if (!require_true(rio_readline(&reader, line, sizeof(line)) == 0, "line EOF")) return 0;
    return 1;
}

static int test_pipe_eof(void) {
    int ends[2];
    char bytes[8] = {0};
    if (pipe(ends) != 0) return 0;
    if (rio_writen(ends[1], "xyz", 3, NULL) != 0 || close(ends[1]) != 0) return 0;
    ssize_t count = rio_readn(ends[0], bytes, 5, NULL);
    int close_result = close(ends[0]);
    return require_true(count == 3 && memcmp(bytes, "xyz", 3) == 0 && close_result == 0,
                        "pipe partial then EOF");
}

static int install_handler(int signal_number, void (*handler)(int)) {
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    action.sa_handler = handler;
    sigemptyset(&action.sa_mask);
    action.sa_flags = 0;
    return sigaction(signal_number, &action, NULL);
}

static int test_masked_reap(void) {
    sigset_t blocked, previous, suspend_mask;
    int status = 0;
    int gate[2] = {-1, -1};
    int parent_gate = -1;
    int success = 0;
    int mask_installed = 0;
    pid_t child = -1;
    sigemptyset(&blocked);
    sigaddset(&blocked, SIGCHLD);
    if (pipe(gate) != 0 || install_handler(SIGCHLD, mark_sigchld) != 0 ||
        install_handler(SIGALRM, mark_timeout) != 0 ||
        sigprocmask(SIG_BLOCK, &blocked, &previous) != 0) goto cleanup;
    mask_installed = 1;

    child = fork();
    if (child < 0) goto cleanup;
    if (child == 0) {
        char release;
        ssize_t received;
        (void)close(gate[1]);
        do {
            received = read(gate[0], &release, 1);
        } while (received < 0 && errno == EINTR);
        (void)close(gate[0]);
        _exit(received == 1 ? 23 : 24);
    }
    if (close(gate[0]) != 0) goto cleanup;
    gate[0] = -1;
    parent_gate = gate[1];
    gate[1] = -1;

    /* The child cannot exit before this gate is released: WNOHANG must be 0. */
    if (waitpid(child, &status, WNOHANG) != 0) goto cleanup;
    sigchld_seen = 0;
    timed_out = 0;
    if (write(parent_gate, "x", 1) != 1 || close(parent_gate) != 0) goto cleanup;
    parent_gate = -1;
    suspend_mask = previous;
    sigdelset(&suspend_mask, SIGCHLD);
    alarm(3);
    while (!sigchld_seen && !timed_out) {
        (void)sigsuspend(&suspend_mask); /* SIGCHLD or the bounded alarm wakes it. */
    }
    alarm(0);
    if (timed_out) goto cleanup;

    /* The SIGCHLD proves a state is available; WNOHANG must now return PID. */
    if (waitpid(child, &status, WNOHANG) != child) goto cleanup;
    errno = 0;
    if (waitpid(child, &status, WNOHANG) != -1 || errno != ECHILD) goto cleanup;
    success = WIFEXITED(status) && WEXITSTATUS(status) == 23;

cleanup:
    alarm(0);
    if (gate[0] >= 0) (void)close(gate[0]);
    if (gate[1] >= 0) (void)close(gate[1]);
    if (parent_gate >= 0) (void)close(parent_gate);
    if (child > 0) {
        while (waitpid(child, &status, 0) < 0 && errno == EINTR) {
        }
    }
    if (mask_installed && sigprocmask(SIG_SETMASK, &previous, NULL) != 0) return 0;
    return require_true(success, "WNOHANG 0, PID, then ECHILD with gated child");
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) {
        if (test_injected_io() && test_pipe_eof() && test_masked_reap()) {
            puts("posix_lab self-test passed");
            return 0;
        }
        return 1;
    }
    fprintf(stderr, "usage: %s --self-test\n", argv[0]);
    return 64;
}
