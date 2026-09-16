/* Benign teaching source: no network, file writes, or intentionally unsafe memory access. */
#include <stdio.h>
int main(int argc, char **argv) {
    if (argc > 2) {
        fputs("usage: hello [name]\n", stderr);
        return 2;
    }
    const char *name = (argc == 2) ? argv[1] : "learner";
    printf("Hello, %s. This is a local teaching program.\n", name);
    return 0;
}
