#include <wwl/measurement.hpp>
#include <wwl/report.hpp>
#include <wwl/report_queue.hpp>
#include <wwl/detail/executor_testing.hpp>
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <memory_resource>
#include <new>
#include <sstream>
#include <string_view>
#include <thread>

// One executable owns these replacements. They are never linked into the library.
// Fixed TLS bookkeeping performs no new/delete; ownership tags survive disarming
// and cross-thread deletion. malloc/OS/stream internals are outside this domain.
namespace fault {
struct State { bool armed=false; std::size_t fail=0, calls=0; bool hit=false; };
thread_local State state;
std::atomic<std::size_t> live_blocks=0, live_bytes=0;
struct alignas(std::max_align_t) Header { void* raw; std::size_t size; bool tracked; };
void* allocate(std::size_t size,std::size_t alignment) {
    const bool tracked=state.armed;
    if (tracked && ++state.calls==state.fail) {state.hit=true;throw std::bad_alloc{};}
    alignment=std::max(alignment,alignof(Header));
    const auto payload=std::max(size,std::size_t{1});
    if (payload>std::numeric_limits<std::size_t>::max()-sizeof(Header)-(alignment-1))
        throw std::bad_alloc{};
    void* raw=std::malloc(payload+sizeof(Header)+alignment-1);
    if (!raw) throw std::bad_alloc{};
    const auto begin=reinterpret_cast<std::uintptr_t>(raw)+sizeof(Header);
    const auto aligned=(begin+alignment-1)&~(static_cast<std::uintptr_t>(alignment)-1);
    auto* header=reinterpret_cast<Header*>(aligned)-1;
    ::new (header) Header{raw,size,tracked};
    if (tracked) {++live_blocks;live_bytes+=size;}
    return reinterpret_cast<void*>(aligned);
}
void release(void* pointer) noexcept {
    if (!pointer) return;
    const auto* header=static_cast<Header*>(pointer)-1;
    if (header->tracked) {--live_blocks;live_bytes-=header->size;}
    std::free(header->raw);
}
struct Scope {
    explicit Scope(std::size_t fail) {state={true,fail,0,false};}
    ~Scope() {state.armed=false;}
    Scope(const Scope&)=delete;
};
}
void* operator new(std::size_t n) {return fault::allocate(n,__STDCPP_DEFAULT_NEW_ALIGNMENT__);}
void* operator new[](std::size_t n) {return ::operator new(n);}
void* operator new(std::size_t n,std::align_val_t a) {return fault::allocate(n,static_cast<std::size_t>(a));}
void* operator new[](std::size_t n,std::align_val_t a) {return ::operator new(n,a);}
void operator delete(void* p) noexcept {fault::release(p);}
void operator delete[](void* p) noexcept {fault::release(p);}
void operator delete(void* p,std::size_t) noexcept {fault::release(p);}
void operator delete[](void* p,std::size_t) noexcept {fault::release(p);}
void operator delete(void* p,std::align_val_t) noexcept {fault::release(p);}
void operator delete[](void* p,std::align_val_t) noexcept {fault::release(p);}
void operator delete(void* p,std::size_t,std::align_val_t) noexcept {fault::release(p);}
void operator delete[](void* p,std::size_t,std::align_val_t) noexcept {fault::release(p);}
void* operator new(std::size_t n,const std::nothrow_t&) noexcept {try{return ::operator new(n);}catch(...){return nullptr;}}
void* operator new[](std::size_t n,const std::nothrow_t& t) noexcept {return ::operator new(n,t);}
void* operator new(std::size_t n,std::align_val_t a,const std::nothrow_t&) noexcept {try{return ::operator new(n,a);}catch(...){return nullptr;}}
void* operator new[](std::size_t n,std::align_val_t a,const std::nothrow_t& t) noexcept {return ::operator new(n,a,t);}
void operator delete(void* p,const std::nothrow_t&) noexcept {fault::release(p);}
void operator delete[](void* p,const std::nothrow_t&) noexcept {fault::release(p);}
void operator delete(void* p,std::align_val_t,const std::nothrow_t&) noexcept {fault::release(p);}
void operator delete[](void* p,std::align_val_t,const std::nothrow_t&) noexcept {fault::release(p);}

namespace {
int failures=0;
void check(bool condition,const char* message) {
    if (!condition) {++failures;std::fprintf(stderr,"FAIL: %s\n",message);}
}
void zero() {check(fault::live_blocks==0 && fault::live_bytes==0,"armed allocation lifetime returned to zero");}
// Isolate ordinary allocations from PMR: PMR uses malloc here, with separate
// block/byte accounting and no fault injection. Original PMR tests stay intact.
class MallocResource final : public std::pmr::memory_resource {
public:
    std::size_t blocks=0,bytes=0;
private:
    void* do_allocate(std::size_t n,std::size_t alignment) override {
        void* p=nullptr;
        if (alignment<=alignof(std::max_align_t)) p=std::malloc(std::max(n,std::size_t{1}));
        else if (posix_memalign(&p,alignment,std::max(n,std::size_t{1}))!=0) p=nullptr;
        if (!p) throw std::bad_alloc{};
        ++blocks;bytes+=n;return p;
    }
    void do_deallocate(void* p,std::size_t n,std::size_t) override {--blocks;bytes-=n;std::free(p);}
    bool do_is_equal(const std::pmr::memory_resource& other) const noexcept override {return this==&other;}
};
std::string codes() {std::string text;for (int i=0;i<64;++i) text+="2 4 6 8 ";return text;}

std::size_t batch_trial(std::size_t fail,const std::string& text) {
    std::size_t calls=0;
    {
        wwl::Batch old({wwl::RawCode{7}},wwl::Calibration{500,2},wwl::Seconds{2});
        const auto view=old.codes();std::istringstream input(text);
        bool threw=false;
        {fault::Scope scope(fail);
         try {wwl::replace_from_stream(old,input);}catch(const std::bad_alloc&) {threw=true;}
         catch(...) {check(false,"valid Batch allocation failure must propagate bad_alloc");}
         calls=fault::state.calls;check(fault::state.hit==(fail!=0),"Batch failure point reached");}
        check(threw==(fail!=0),"Batch success/exception layer");
        if (fail) {
            check(old.codes().data()==view.data() && old.codes().size()==1 && view[0].value()==7,
                  "Batch old codes and borrowing address unchanged");
            check(old.calibration().gain()==500 && old.calibration().offset()==2 && old.interval().value==2,
                  "Batch old calibration and interval unchanged");zero();
        } else check(old.codes().size()==256,"Batch candidate committed");
    }
    zero();return calls;
}
std::size_t session_trial(std::size_t fail,const std::string& text) {
    MallocResource resource;std::size_t calls=0;
    {
        wwl::ReportSession session(&resource);std::istringstream old("2 4 6 8");
        session.replace(old,wwl::ReportSettings{});
        const auto window=session.windows();const auto old_text=session.text();
        const std::string saved(old_text);const auto blocks=resource.blocks,bytes=resource.bytes;
        std::istringstream next(text);bool threw=false;
        const wwl::ReportSettings settings{wwl::Calibration{500,3},std::chrono::milliseconds{2},
                                          wwl::WindowSpec{4,2},"abcdefghijklmnopqrstuvwxyz0123456789ABCD"};
        {fault::Scope scope(fail);
         try {session.replace(next,settings);}catch(const std::bad_alloc&) {threw=true;}
         catch(...) {check(false,"Session ordinary allocation failure must propagate bad_alloc");}
         calls=fault::state.calls;check(fault::state.hit==(fail!=0),"Session ordinary failure point reached");}
        check(threw==(fail!=0),"Session ordinary success/exception layer");
        if (fail) {
            check(session.windows().data()==window.data() && session.windows().size()==window.size(),
                  "Session old window borrowing address and count unchanged");
            check(session.text().data()==old_text.data() && session.text()==saved,"Session old text preserved");
            const auto retained=session.settings();
            check(retained->calibration().gain()==1000 && retained->calibration().offset()==0 &&
                  retained->interval().count()==1000 && retained->window().width()==2 &&
                  retained->window().hop()==1 && retained->label()=="measurement",
                  "Session all old settings preserved");
            for (std::size_t i=0;i<window.size();++i) {
                check(window[i].begin==i && window[i].end==i+2 &&
                      window[i].statistics.mean.value==3+2*i &&
                      window[i].statistics.population_variance.value==1,
                      "Session old borrowed windows retain contents");
            }
            check(resource.blocks==blocks && resource.bytes==bytes,"PMR candidate resources restored");zero();
        } else check(session.windows().size()==127,"Session new candidate committed");
    }
    zero();check(resource.blocks==0 && resource.bytes==0,"Session PMR malloc resources zero");return calls;
}
std::size_t queue_trial(std::size_t fail) {
    std::size_t calls=0;
    {
        wwl::BoundedReportQueue queue(8);
        std::array<wwl::WorkItem,512> items;
        for (std::size_t i=0;i<items.size();++i) items[i]={i,{std::string(200,'x'),wwl::ReportSettings{}}};
        check(queue.push(std::move(items[0])),"queue old sentinel accepted");
        std::size_t accepted=1;bool threw=false;
        {fault::Scope scope(fail);
         try {
             // Queue remains at one accepted item. Advancing the deque far enough
             // reaches actual block/map growth without assuming block size.
             for (;accepted<items.size();++accepted) {
                 check(queue.push(std::move(items[accepted])),"queue push accepted");
                 auto prior=queue.pop();
                 check(prior && prior->index==accepted-1 && prior->task.input.size()==200,
                       "queue advancing FIFO preserves each previous payload");
             }
         }
         catch(const std::bad_alloc&) {threw=true;}
         catch(...) {check(false,"queue insertion failure must propagate bad_alloc");}
         calls=fault::state.calls;check(fault::state.hit==(fail!=0),"deque insertion failure point reached");}
        check(threw==(fail!=0),"queue insertion success/exception layer");
        const auto snap=queue.snapshot();
        check(snap.state==wwl::QueueState::open && snap.queued==1 &&
              snap.producers_waiting==0 && snap.consumers_waiting==0,"failed push retains old queue state");
        queue.close();
        auto retained=queue.pop();
        check(retained && retained->index==accepted-1 && retained->task.input.size()==200,
              "failed push preserves previous front and owned payload");
        check(!queue.pop(),"queue drains after insertion fault");
    }
    zero();return calls;
}
struct Threads {std::atomic<int> launched=0,active=0,exited=0;std::atomic<std::size_t> calls=0;std::atomic<bool> hit=false;};
std::size_t executor_trial(std::size_t fail,bool worker_domain,const std::string& text) {
    Threads threads;std::size_t calls=0;
    {
        std::vector<wwl::ReportTask> tasks;
        for (int i=0;i<2;++i) tasks.push_back({text,wwl::ReportSettings{}});
        const wwl::detail::WorkerLauncher launch=[&](std::function<void()> body) {
            auto thread=std::jthread([&,body=std::move(body)] {
                ++threads.active;
                if (worker_domain) {
                    fault::Scope scope(fail);body();
                    threads.calls=fault::state.calls;threads.hit=fault::state.hit;
                } else body();
                --threads.active;++threads.exited;
            });
            ++threads.launched;return thread;
        };
        bool threw=false;
        std::vector<wwl::TaskOutcome> results;
        {fault::Scope scope(worker_domain?0:fail);
         // Main thread excluded entirely for the worker sweep.
         if (worker_domain) fault::state.armed=false;
         try {results=wwl::detail::run_reports_with_launcher(std::move(tasks),{1,1},{},launch);}
         catch(const std::bad_alloc&) {threw=true;}
         catch(...) {check(false,"executor dispatch exception layer");}
         calls=worker_domain?threads.calls.load():fault::state.calls;
         check((worker_domain?threads.hit.load():fault::state.hit)==(fail!=0),"executor allocation failure point reached");}
        check(threads.active==0 && threads.exited==threads.launched,"every started real thread exited before propagation/return");
        if (worker_domain) {
            check(!threw && results.size()==2,"worker allocation failure becomes task outcome");
            std::size_t failed=0,completed=0;
            for (const auto& result:results) {
                if (result.state==wwl::TaskState::failed) {
                    ++failed;
                    check(result.report.empty() && std::string_view(result.diagnostic.data())==std::bad_alloc{}.what(),
                          "bad_alloc becomes fixed failure diagnostic without report");
                }
                else if (result.state==wwl::TaskState::completed) {++completed;check(!result.report.empty(),"later/earlier independent task has owning report");}
                else check(false,"one-shot allocation fault does not cancel independent task");
            }
            check(failed==(fail?1u:0u) && completed==(fail?1u:2u),"worker failure isolated to one task");
        } else {
            check(threw==(fail!=0),"management allocation failure rethrows after join");
            if (!fail) check(results.size()==2 && results[0].state==wwl::TaskState::completed &&
                             results[1].state==wwl::TaskState::completed,"executor normal result delivered");
        }
    }
    zero();return calls;
}
void batch_copy() {
    wwl::Batch old({wwl::RawCode{2},wwl::RawCode{4}});
    const auto original=old.codes();
    for (std::size_t point:{0u,1u}) {
        bool threw=false;
        {fault::Scope scope(point);
         try {auto copy=old;check(copy.codes().data()!=original.data() && copy.codes()[1].value()==4,
                                 "Batch copy owns separate codes");}
         catch(const std::bad_alloc&) {threw=true;}
         check(fault::state.calls==1 && fault::state.hit==(point!=0),"Batch copy single observed allocation");}
        check(threw==(point!=0) && old.codes().data()==original.data() && original[0].value()==2,
              "failed Batch copy leaves source and borrow unchanged");zero();
    }
}
void stream_layer() {
    // A long invalid token forces an ordinary string growth. basic_istream may
    // catch the injected bad_alloc and set badbit unless its exception mask asks
    // for propagation. The old Batch still stays intact in both cases.
    for (bool rethrow:{false,true}) {
        wwl::Batch old({wwl::RawCode{7}});const auto pointer=old.codes().data();
        std::istringstream input(std::string(200,'1'));
        if (rethrow) input.exceptions(std::ios::badbit);
        bool layer=false;
        {fault::Scope scope(1);
         try {wwl::replace_from_stream(old,input);}
         catch(const std::bad_alloc&) {layer=rethrow;}
         catch(const std::runtime_error&) {layer=!rethrow;}
         catch(...) {}
         check(fault::state.hit,"token string failure injected");}
        check(layer && input.bad() && old.codes().data()==pointer && old.codes()[0].value()==7,
              "istream mask selects exception layer; Batch retained");
        zero();
    }
}
}
int main() {
    try {
        // Warm stream/locale initialization before any scoped injection.
        {std::istringstream warm("2 4");(void)wwl::read_batch(warm);}
        // The default new alignment can exceed max_align_t (Apple arm64).
        void* ordinary=::operator new(1);
        check(reinterpret_cast<std::uintptr_t>(ordinary)%__STDCPP_DEFAULT_NEW_ALIGNMENT__==0,
              "replacement ordinary new respects its default alignment");
        ::operator delete(ordinary);
        void* aligned=::operator new(1,std::align_val_t{64});
        check(reinterpret_cast<std::uintptr_t>(aligned)%64==0,"replacement aligned new respects over-alignment");
        ::operator delete(aligned,std::align_val_t{64});
        {fault::Scope scope(1);check(::operator new(1,std::nothrow)==nullptr && fault::state.hit,
                                   "nothrow replacement maps injected bad_alloc to nullptr");}
        zero();
        const auto text=codes();
        const auto batch=batch_trial(0,text);check(batch>0,"Batch baseline allocates");
        for (std::size_t k=1;k<=batch;++k) batch_trial(k,text);
        const auto session=session_trial(0,text);check(session>batch,"ordinary long-label allocation also reached");
        for (std::size_t k=1;k<=session;++k) session_trial(k,text);
        const auto queue=queue_trial(0);check(queue>0,"deque baseline insertion allocates");
        for (std::size_t k=1;k<=queue;++k) queue_trial(k);
        const auto management=executor_trial(0,false,text);check(management>0,"management baseline allocates");
        for (std::size_t k=1;k<=management;++k) executor_trial(k,false,text);
        const auto worker=executor_trial(0,true,text);check(worker>0,"worker baseline allocates");
        for (std::size_t k=1;k<=worker;++k) executor_trial(k,true,text);
        batch_copy();stream_layer();
        std::printf("ordinary allocation failure points: batch=%zu session=%zu queue=%zu management=%zu worker=%zu; live_blocks=%zu live_bytes=%zu failures=%d\n",
                    batch,session,queue,management,worker,fault::live_blocks.load(),fault::live_bytes.load(),failures);
    } catch(const std::exception& e) {std::fprintf(stderr,"unexpected test exception: %s\n",e.what());return 1;}
    return failures?1:0;
}
