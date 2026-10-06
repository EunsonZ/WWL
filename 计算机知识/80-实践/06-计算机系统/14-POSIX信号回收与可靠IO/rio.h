#ifndef WWL_POSIX_RIO_H
#define WWL_POSIX_RIO_H

#include <stddef.h>
#include <sys/types.h>

typedef ssize_t (*rio_transfer_fn)(int fd, void *buffer, size_t count, void *context);

typedef struct {
    rio_transfer_fn read_fn;
    rio_transfer_fn write_fn;
    void *context;
} rio_hooks;

typedef struct {
    int fd;
    rio_hooks hooks;
    unsigned char buffer[64];
    size_t start;
    size_t end;
} rio_reader;

ssize_t rio_readn(int fd, void *buffer, size_t count, const rio_hooks *hooks);
int rio_writen(int fd, const void *buffer, size_t count, const rio_hooks *hooks);
void rio_reader_init(rio_reader *reader, int fd, const rio_hooks *hooks);
/* Returns a line byte count, 0 for EOF before any byte, or -1 with errno. */
ssize_t rio_readline(rio_reader *reader, char *destination, size_t capacity);

#endif
