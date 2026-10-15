#pragma once

#include <cstddef>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>

template <class T>
class TensorBuffer {
public:
    explicit TensorBuffer(std::vector<std::size_t> shape)
        : shape_(std::move(shape)), data_(checked_element_count(shape_)) {}

    const std::vector<std::size_t> & shape() const noexcept { return shape_; }
    std::size_t size() const noexcept { return data_.size(); }

    T & at(const std::vector<std::size_t> & index) { return data_.at(flat_index(index)); }
    const T & at(const std::vector<std::size_t> & index) const { return data_.at(flat_index(index)); }

private:
    static std::size_t checked_element_count(const std::vector<std::size_t> & shape) {
        if (shape.empty()) {
            throw std::invalid_argument("tensor rank must be at least one");
        }
        std::size_t count = 1;
        for (const auto extent : shape) {
            if (extent == 0 || count > std::numeric_limits<std::size_t>::max() / extent) {
                throw std::invalid_argument("invalid or overflowing tensor shape");
            }
            count *= extent;
        }
        return count;
    }

    std::size_t flat_index(const std::vector<std::size_t> & index) const {
        if (index.size() != shape_.size()) {
            throw std::out_of_range("index rank does not match tensor rank");
        }
        std::size_t offset = 0;
        for (std::size_t axis = 0; axis < shape_.size(); ++axis) {
            if (index[axis] >= shape_[axis]) {
                throw std::out_of_range("tensor index is outside its shape");
            }
            offset = offset * shape_[axis] + index[axis];
        }
        return offset;
    }

    std::vector<std::size_t> shape_;
    std::vector<T> data_;
};
