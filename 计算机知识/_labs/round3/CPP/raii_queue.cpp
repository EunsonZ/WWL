#include <cassert>
#include <condition_variable>
#include <deque>
#include <iostream>
#include <memory>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <thread>
#include <vector>
struct Guard {
    int id; std::vector<int>& log;
    Guard(int i, std::vector<int>& l):id(i),log(l){log.push_back(id);}
    ~Guard(){ log.push_back(-id); } // test reserves capacity so no allocation here
    Guard(const Guard&)=delete;
    Guard& operator=(const Guard&)=delete;
};
class Queue {
    std::mutex m; std::condition_variable readable,writable;
    std::deque<int> q; const std::size_t cap; bool closed=false;
public:
    explicit Queue(std::size_t c):cap(c){if(!c)throw std::invalid_argument("zero capacity");}
    bool push(int x){
        std::unique_lock lock(m);
        writable.wait(lock,[&]{return closed || q.size()<cap;});
        if(closed)return false;
        q.push_back(x); readable.notify_one(); return true;
    }
    std::optional<int> pop(){
        std::unique_lock lock(m);
        readable.wait(lock,[&]{return closed || !q.empty();});
        if(q.empty())return std::nullopt;
        int v=q.front();q.pop_front();writable.notify_one();return v;
    }
    void close(){std::lock_guard lock(m);closed=true;readable.notify_all();writable.notify_all();}
};
int main(){
    std::vector<int> log;log.reserve(4);
    try {Guard a(1,log);Guard b(2,log);throw std::runtime_error("test");}
    catch(const std::runtime_error&){}
    assert((log==std::vector<int>{1,2,-2,-1}));
    auto p=std::make_unique<int>(7);auto q=std::move(p);assert(!p && *q==7);
    Queue queue(7); long long total=0;
    std::jthread producer([&]{for(int i=0;i<10000;i++)assert(queue.push(i));queue.close();});
    std::jthread consumer([&]{while(auto x=queue.pop())total+=*x;});
    producer.join();consumer.join();
    assert(total==49995000);assert(!queue.push(1));assert(!queue.pop());
    std::cout<<"PASS: reverse cleanup, unique ownership, bounded queue close/drain\n";
}
