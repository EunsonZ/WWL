#pragma once

#include <cstddef>
#include <map>
#include <string>
#include <string_view>

std::map<std::string, std::size_t> count_words(std::string_view text);
