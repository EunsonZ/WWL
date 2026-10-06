#include <atomic>
#include <cassert>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <type_traits>
#include <utility>
#include <vector>

int target(int&) {return 1;}
int target(const int&) {return 2;}
int target(int&&) {return 3;}
template<class T> decltype(auto) relay(T&& value) {return target(std::forward<T>(value));}

struct CopyTrack {
    static inline int copies=0,moves=0;
    CopyTrack()=default;
    CopyTrack(const CopyTrack&) {++copies;}
    CopyTrack(CopyTrack&&) noexcept {++moves;}
};
struct Throwing {
    static inline int alive=0,budget=-1;
    int value;
    explicit Throwing(int v):value(v){++alive;}
    Throwing(const Throwing& other):value(other.value){
        if(budget==0) throw std::runtime_error("injected copy failure");
        if(budget>0) --budget;
        ++alive;
    }
    Throwing(Throwing&& other) noexcept:value(other.value){++alive;}
    Throwing& operator=(const Throwing&)=default;
    ~Throwing(){--alive;}
};
struct TestConfig {
    std::string name;
    std::vector<Throwing> values;
    void swap(TestConfig& other) noexcept {name.swap(other.name);values.swap(other.values);}
};
void replace(TestConfig& live,const TestConfig& input){TestConfig candidate=input;live.swap(candidate);}
std::vector<int> values(const TestConfig& c){std::vector<int> out;for(auto& v:c.values)out.push_back(v.value);return out;}

int main(){
    int x=7;const int cx=8;
    auto a=cx;auto& b=cx;decltype(auto) c=(x);
    static_assert(std::is_same_v<decltype(a),int>);
    static_assert(std::is_same_v<decltype(b),const int&>);
    static_assert(std::is_same_v<decltype(c),int&>);
    static_assert(std::is_same_v<decltype(x),int>);
    static_assert(std::is_same_v<decltype((x)),int&>);
    c=9;assert(x==9);assert(relay(x)==1);assert(relay(cx)==2);assert(relay(4)==3);
    const CopyTrack const_value;CopyTrack copy(std::move(const_value));
    (void)copy;assert(CopyTrack::copies==1&&CopyTrack::moves==0);
    {
        TestConfig live{"old",{}};live.values.emplace_back(8);live.values.emplace_back(9);
        TestConfig input{"new",{}};for(int i=0;i<12;++i)input.values.emplace_back(i);
        const int baseline=Throwing::alive;
        for(int point=0;point<12;++point){
            Throwing::budget=point;bool threw=false;
            try{replace(live,input);}catch(const std::runtime_error&){threw=true;}
            Throwing::budget=-1;
            assert(threw&&live.name=="old");assert((values(live)==std::vector<int>{8,9}));assert(Throwing::alive==baseline);
        }
        replace(live,input);assert(values(live)==values(input));replace(live,live);assert(values(live)==values(input));
        TestConfig empty{"empty",{}};replace(live,empty);assert(live.values.empty());
    }
    assert(Throwing::alive==0);
    {
        std::vector<int> v{10,20,30,40};v.reserve(16);auto* first=&v[0];const auto capacity=v.capacity();
        v.erase(v.begin()+2);assert(v.capacity()==capacity);assert(*first==10);assert((v==std::vector<int>{10,20,40}));
        // Do not access pointers/iterators at or after the erased position.
        std::string owned="safe text";std::string_view view=owned;assert(view=="safe text");
    }
    for(int i=0;i<50;++i){
        int payload=0;std::atomic<bool> ready{false};int observed=0;
        std::thread reader([&]{while(!ready.load(std::memory_order_acquire))std::this_thread::yield();observed=payload;});
        payload=42;ready.store(true,std::memory_order_release);reader.join();assert(observed==42);
    }
    std::atomic<int> counter{0};const int old1=counter.load(),old2=counter.load();counter.store(old1+1);counter.store(old2+1);assert(counter.load()==1);
    counter.store(0);counter.fetch_add(1);counter.fetch_add(1);assert(counter.load()==2);
    std::cout<<"C++ deduction, lifetime-safe views, 12 copy-failure points and publication checks passed\n";
}
