CC = clang
AR = ar
BUILD = build
CPPFLAGS = -Iinclude
CFLAGS = -std=c17 -O2 -g -Wall -Wextra -Wpedantic -Wconversion -Werror
LDLIBS = -lm

all: $(BUILD)/first_input $(BUILD)/measure $(BUILD)/wordfreq $(BUILD)/test_measure
$(BUILD):
	mkdir -p $@
$(BUILD)/first_input: src/first_input.c | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< -o $@
$(BUILD)/measure.o: src/measure.c include/measure.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(BUILD)/wordfreq.o: src/wordfreq.c include/wordfreq.h include/measure.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(BUILD)/libmeasure.a: $(BUILD)/measure.o $(BUILD)/wordfreq.o
	$(AR) rcs $@ $^
$(BUILD)/measure: src/main.c $(BUILD)/libmeasure.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(BUILD)/libmeasure.a $(LDLIBS) -o $@
$(BUILD)/wordfreq: src/wordfreq_main.c $(BUILD)/libmeasure.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(BUILD)/libmeasure.a $(LDLIBS) -o $@
$(BUILD)/test_measure: tests/test_measure.c $(BUILD)/libmeasure.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(BUILD)/libmeasure.a $(LDLIBS) -o $@
test: all
	$(BUILD)/test_measure
	python3 tests/test_cli.py $(BUILD)
.PHONY: all test

# macOS/BSD FILE fault experiment: unsupported hosts return 77 explicitly.
$(BUILD)/test_io_faults: tests/test_io_faults.c src/main.c $(BUILD)/libmeasure.a
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(BUILD)/libmeasure.a $(LDLIBS) -o $@
io-fault-test: $(BUILD)/test_io_faults
	$(BUILD)/test_io_faults
.PHONY: io-fault-test
