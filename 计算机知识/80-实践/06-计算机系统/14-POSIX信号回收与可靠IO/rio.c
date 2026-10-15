#include "rio.h"

#include <errno.h>
#include <string.h>
#include <unistd.h>

static ssize_t system_read(int fd, void *buffer, size_t count, void *context) {
    (void)context;
    return read(fd, buffer, count);
}

static ssize_t system_write(int fd, void *buffer, size_t count, void *context) {
    (void)context;
    return write(fd, buffer, count);
}

static rio_transfer_fn choose_read(const rio_hooks *hooks) {
    return hooks != NULL && hooks->read_fn != NULL ? hooks->read_fn : system_read;
}

static rio_transfer_fn choose_write(const rio_hooks *hooks) {
    return hooks != NULL && hooks->write_fn != NULL ? hooks->write_fn : system_write;
}

static void *choose_context(const rio_hooks *hooks) {
    return hooks == NULL ? NULL : hooks->context;
}

ssize_t rio_readn(int fd, void *buffer, size_t count, const rio_hooks *hooks) {
    unsigned char *next = buffer;
    size_t remaining = count;
    rio_transfer_fn transfer = choose_read(hooks);

    if (count == 0) {
        return 0;
    }
    while (remaining != 0) {
        ssize_t received = transfer(fd, next, remaining, choose_context(hooks));
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (received == 0) {
            break; /* EOF: the valid prefix is [buffer, next). */
        }
        if ((size_t)received > remaining) {
            errno = EIO;
            return -1;
        }
        next += received;
        remaining -= (size_t)received;
    }
    return (ssize_t)(count - remaining);
}

int rio_writen(int fd, const void *buffer, size_t count, const rio_hooks *hooks) {
    const unsigned char *next = buffer;
    size_t remaining = count;
    rio_transfer_fn transfer = choose_write(hooks);

    if (count == 0) {
        return 0;
    }
    while (remaining != 0) {
        ssize_t sent = transfer(fd, (void *)next, remaining, choose_context(hooks));
        if (sent < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (sent == 0 || (size_t)sent > remaining) {
            errno = EIO; /* A positive-length write made no usable progress. */
            return -1;
        }
        next += sent;
        remaining -= (size_t)sent;
    }
    return 0;
}

void rio_reader_init(rio_reader *reader, int fd, const rio_hooks *hooks) {
    memset(reader, 0, sizeof(*reader));
    reader->fd = fd;
    if (hooks != NULL) {
        reader->hooks = *hooks;
    }
}

static int rio_next_byte(rio_reader *reader, unsigned char *out) {
    rio_transfer_fn transfer = choose_read(&reader->hooks);
    for (;;) {
        if (reader->start < reader->end) {
            *out = reader->buffer[reader->start++];
            return 1;
        }
        ssize_t received = transfer(reader->fd, reader->buffer, sizeof(reader->buffer),
                                    choose_context(&reader->hooks));
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (received == 0) {
            return 0;
        }
        if ((size_t)received > sizeof(reader->buffer)) {
            errno = EIO;
            return -1;
        }
        reader->start = 0;
        reader->end = (size_t)received;
    }
}

ssize_t rio_readline(rio_reader *reader, char *destination, size_t capacity) {
    size_t used = 0;
    int too_long = 0;

    if (capacity == 0) {
        errno = EINVAL;
        return -1;
    }
    for (;;) {
        unsigned char byte = 0;
        int result = rio_next_byte(reader, &byte);
        if (result < 0) {
            return -1;
        }
        if (result == 0) {
            if (used == 0 && !too_long) {
                return 0;
            }
            break;
        }
        if (!too_long && used + 1 < capacity) {
            destination[used++] = (char)byte;
        } else {
            too_long = 1;
        }
        if (byte == '\n') {
            break;
        }
    }
    destination[used] = '\0';
    if (too_long) {
        errno = EOVERFLOW;
        return -1;
    }
    return (ssize_t)used;
}
