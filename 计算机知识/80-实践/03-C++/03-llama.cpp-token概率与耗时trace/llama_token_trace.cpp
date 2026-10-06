#include "trace_math.hpp"

#include <llama.h>

#include <cstdlib>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

namespace {
struct ModelDeleter {
    void operator()(llama_model * model) const { llama_model_free(model); }
};

struct ContextDeleter {
    void operator()(llama_context * context) const { llama_free(context); }
};

struct Batch {
    explicit Batch(int tokens) : value(llama_batch_init(tokens, 0, 1)) {}
    ~Batch() { llama_batch_free(value); }
    Batch(const Batch&) = delete;
    Batch& operator=(const Batch&) = delete;
    llama_batch value;
};

struct BackendGuard {
    ~BackendGuard() { llama_backend_free(); }
};

std::string token_piece(const llama_vocab * vocab, llama_token token) {
    std::vector<char> buffer(128);
    int count = llama_token_to_piece(vocab, token, buffer.data(), buffer.size(), 0, true);
    if (count < 0) {
        buffer.resize(static_cast<std::size_t>(-count));
        count = llama_token_to_piece(vocab, token, buffer.data(), buffer.size(), 0, true);
    }
    return count >= 0 ? std::string(buffer.data(), static_cast<std::size_t>(count)) : "<unprintable>";
}
}  // namespace

int main(int argc, char * argv[]) {
    if (argc != 3) {
        std::cerr << "usage: llama_token_trace MODEL.GGUF PROMPT\n";
        return EXIT_FAILURE;
    }

    llama_backend_init();
    BackendGuard backend_guard;

    auto model_params = llama_model_default_params();
    model_params.n_gpu_layers = 0;  // CPU trace: record a different value explicitly when comparing.
    std::unique_ptr<llama_model, ModelDeleter> model(
        llama_model_load_from_file(argv[1], model_params));
    if (!model) {
        std::cerr << "could not load the local GGUF model\n";
        return EXIT_FAILURE;
    }
    const llama_vocab * vocab = llama_model_get_vocab(model.get());
    const std::string prompt = argv[2];
    const int count = -llama_tokenize(vocab, prompt.c_str(), prompt.size(), nullptr, 0, true, true);
    if (count <= 0) {
        std::cerr << "could not tokenize prompt\n";
        return EXIT_FAILURE;
    }
    std::vector<llama_token> tokens(static_cast<std::size_t>(count));
    if (llama_tokenize(vocab, prompt.c_str(), prompt.size(), tokens.data(), count, true, true) < 0) {
        std::cerr << "tokenization buffer was unexpectedly too small\n";
        return EXIT_FAILURE;
    }

    auto context_params = llama_context_default_params();
    context_params.n_ctx = 512;
    context_params.n_batch = 512;
    if (count > static_cast<int>(context_params.n_ctx) ||
        count > static_cast<int>(context_params.n_batch)) {
        std::cerr << "prompt token count " << count
                  << " exceeds this lesson's n_ctx/n_batch limit of 512\n";
        return EXIT_FAILURE;
    }
    std::unique_ptr<llama_context, ContextDeleter> context(
        llama_init_from_model(model.get(), context_params));
    if (!context) {
        std::cerr << "could not create context\n";
        return EXIT_FAILURE;
    }

    Batch batch(count);
    for (int i = 0; i < count; ++i) {
        batch.value.token[i] = tokens[static_cast<std::size_t>(i)];
        batch.value.pos[i] = i;
        batch.value.n_seq_id[i] = 1;
        batch.value.seq_id[i][0] = 0;
        batch.value.logits[i] = i == count - 1;
    }
    const int64_t started_us = llama_time_us();
    const int decode_result = llama_decode(context.get(), batch.value);
    if (decode_result != 0) {
        std::cerr << "llama_decode returned " << decode_result << '\n';
        return EXIT_FAILURE;
    }
    llama_synchronize(context.get());
    const int64_t elapsed_us = llama_time_us() - started_us;

    const float * logits = llama_get_logits_ith(context.get(), count - 1);
    if (logits == nullptr) {
        std::cerr << "last prompt token did not produce logits\n";
        return EXIT_FAILURE;
    }
    const auto top = top_probabilities(logits, llama_vocab_n_tokens(vocab), 5);
    std::cout << "trace,prompt_tokens=" << count << ",prefill_us=" << elapsed_us
              << ",n_ctx=" << llama_n_ctx(context.get()) << ",gpu_layers=0\n";
    for (const auto & item : top) {
        std::cout << "top_token,id=" << item.id << ",probability=" << item.probability
                  << ",piece=" << token_piece(vocab, item.id) << '\n';
    }
}
