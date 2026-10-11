CC = /usr/bin/clang
CXX = /usr/bin/clang++
AR = /usr/bin/ar
RUSTC = rustc
BUILD = build-stage4
CPPFLAGS = -I../include -I.
CFLAGS = -std=c17 -O2 -g -Wall -Wextra -Wpedantic -Wconversion -Werror
CXXFLAGS = -std=c++17 -O2 -g -Wall -Wextra -Wpedantic -Wconversion -Werror
LDLIBS = -lm
CHECK_ARGS =
all: $(BUILD)/probe $(BUILD)/thread_queue $(BUILD)/test_fixed $(BUILD)/abi_consumer
$(BUILD):
	mkdir -p $@
$(BUILD)/probe: probe.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@
$(BUILD)/measure.o: ../src/measure.c ../include/measure.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(BUILD)/cabi.o: cabi.c cabi.h ../include/measure.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(BUILD)/libcabi.a: $(BUILD)/measure.o $(BUILD)/cabi.o
	$(AR) rcs $@ $^
$(BUILD)/fixed.o: fixed.c fixed.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -ffreestanding -fno-builtin -c $< -o $@
$(BUILD)/test_fixed: test_fixed.c $(BUILD)/fixed.o
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(BUILD)/fixed.o -o $@
$(BUILD)/thread_queue: thread_queue.c $(BUILD)/measure.o
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(BUILD)/measure.o $(LDLIBS) -o $@
$(BUILD)/abi_consumer: abi_consumer.cpp cabi.h $(BUILD)/libcabi.a
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< $(BUILD)/libcabi.a $(LDLIBS) -o $@
test: all
	python3 run_checks.py $(BUILD) $(CHECK_ARGS)
$(BUILD)/abi_consumer_rust: abi_consumer.rs $(BUILD)/libcabi.a
	$(RUSTC) --edition=2021 -C codegen-units=1 $< -L native=$(BUILD) -l static=cabi -l m -o $@
rust-test: $(BUILD)/abi_consumer_rust
	$(BUILD)/abi_consumer_rust
.PHONY: all test rust-test

# Separate full header/link/runtime check; 77 remains unsupported, not PASS.
THREAD_BUILD = build-thread-capability
thread-capability:
	python3 check_threads.py --cc "$(CC)" --build "$(THREAD_BUILD)"
.PHONY: thread-capability
